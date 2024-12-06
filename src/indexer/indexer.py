from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from azure.storage.blob import BlobServiceClient
import os
import uuid
import json
import logging

class InputBody(BaseModel):
    input: str


class StatusBody(BaseModel):
    status: str


load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

servicebus_connection_string = os.getenv("SERVICEBUS_CONNECTION_STRING")

# Azure Storage Blob client setup
blob_service_client = BlobServiceClient.from_connection_string(os.getenv("STORAGE_CONNECTION_STRING"))
container_name = "uploads"

status_cache = {}
app = FastAPI()

# Disable CORS checking
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

@app.post("/index")
async def index(inputBody: InputBody):
    input = inputBody.input
    logger.info(f"Received input: {input}")

    # Generate a uuid for the request
    request_id = str(uuid.uuid4())
    status_cache[request_id] = "Creating"
    logger.info(f"Generated request_id: {request_id}")

    message = {
        "request_id": request_id,
        "input": input
    }
    logger.info(f"Created message: {message}")

    queue = 'note'
    # If it is a URL
    if input.startswith("http"):
        queue = 'website'
    logger.info(f"Determined queue: {queue}")

    # Send the message to the Service Bus
    with ServiceBusClient.from_connection_string(servicebus_connection_string) as client:
        with client.get_queue_sender(queue) as sender:
            # Encode the service bus message dict as JSON string
            message_json = json.dumps(message)
            servicebus_message = ServiceBusMessage(message_json)
            sender.send_messages(servicebus_message)
            # Update the status
            status_cache[request_id] = "Queued"

    return {"request_id": request_id}

@app.post("/index_file")
async def upload_file(file: UploadFile = File(...)):
    logger.info('Received file: ' + file.filename)

    if (file.filename.lower().endswith(".pdf")):
        queue = 'pdf'
    elif (file.filename.lower().endswith(".docx")):
        queue = 'word'
    else:
        logger.error(f"Unsupported file type.")
        raise HTTPException(status_code=400, detail="Unsupported file type")
    logger.info(f"Determined queue: {queue}")

    request_id = str(uuid.uuid4())
    status_cache[request_id] = "Creating"
    logger.info(f"Generated request_id: {request_id}")

    # Upload the file to Azure Blob Storage
    try:
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=file.filename)
        blob_client.upload_blob(file.file, blob_type="BlockBlob", overwrite=True)
        logger.info(f"Uploaded file to Azure Blob Storage: {request_id}_{file.filename}")
    except Exception as e:
        logger.error(f"Error uploading file to Azure Blob Storage: {e}")
        raise HTTPException(status_code=500, detail="Error uploading file to Azure Blob Storage")

    message = {
        "request_id": request_id,
        "file_name": file.filename,
        "file_container": container_name,
        "file_location": blob_client.url
    }
    logger.info(f"Created message: {message}")

    # Send the message to the Service Bus
    with ServiceBusClient.from_connection_string(servicebus_connection_string) as client:
        with client.get_queue_sender(queue) as sender:
            # Encode the service bus message dict as JSON string
            servicebus_message = ServiceBusMessage(json.dumps(message))
            sender.send_messages(servicebus_message)
            # Update the status
            status_cache[request_id] = "Queued"

    return {"request_id": request_id, "file_location": blob_client.url}

@app.get("/status/{request_id}")
async def status(request_id: str):
    # If request_id is not found, return HTTP 404
    if request_id not in status_cache:
        raise HTTPException(status_code=404, detail="Request ID not found")
    return {"status": status_cache.get(request_id)}


@app.post("/status/{request_id}")
async def update_status(request_id: str, statusBody: StatusBody):
    status_cache[request_id] = statusBody.status
    return {"status": status_cache[request_id]}
