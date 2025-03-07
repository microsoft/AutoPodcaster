# Add the parent directory to the system path
from fastapi.responses import JSONResponse
import logging
import json
import uuid
import os
from azure.storage.blob import BlobServiceClient
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from azure.cosmos import CosmosClient, exceptions as cosmos_exceptions
from dotenv import load_dotenv
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, File, UploadFile, HTTPException
import datetime

from autopodcaster_model import Input

# ---------------------------------------------------------------------------- #
#                                    Config                                    #
# ---------------------------------------------------------------------------- #

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

servicebus_connection_string = os.getenv("SERVICEBUS_CONNECTION_STRING")

# Azure Cosmsos DB client setup
cosmosdb_connection_string = os.getenv("COSMOSDB_CONNECTION_STRING")
cosmosdb_client = CosmosClient.from_connection_string(
    cosmosdb_connection_string)
database_name = "autopodcaster"
database_client = cosmosdb_client.get_database_client(database_name)
container_name = "inputs"
container_client = database_client.get_container_client(container_name)

# Azure Storage Blob client setup
blob_service_client = BlobServiceClient.from_connection_string(
    os.getenv("STORAGE_CONNECTION_STRING"))
blob_container_name = "uploads"

# ---------------------------------------------------------------------------- #
#                                     Model                                    #
# ---------------------------------------------------------------------------- #


class InputBody(BaseModel):
    input: str


class StatusBody(BaseModel):
    status: str

# ---------------------------------------------------------------------------- #
#                                   Functions                                  #
# ---------------------------------------------------------------------------- #


def save_to_cosmosdb(input: Input):
    """Save input object to Cosmos DB"""
    container_client.create_item(body=input.to_dict())


def get_input_by_id_as_dict(request_id: str):
    """Get input by ID from Cosmos DB"""
    try:
        response = container_client.read_item(
            item=request_id, partition_key=request_id)
        return response
    except cosmos_exceptions.CosmosResourceNotFoundError:
        return None


def get_all_inputs_as_dict():
    """Get all inputs from Cosmos DB"""
    query = """
    SELECT c.id, c.title, c.date, c.last_updated, c.status, c.author,
           c.description, c.source, c.type, c.thumbnail_url, c.topics, c.entities,
           c.content
    FROM c
    """
    items = container_client.query_items(
        query=query,
        enable_cross_partition_query=True
    )
    return list(items)


def get_inputs_by_status(status: str):
    """Get inputs with specific status from Cosmos DB"""
    query = """
    SELECT c.id, c.title, c.date, c.last_updated, c.status, c.author,
           c.description, c.source, c.type, c.thumbnail_url, c.topics, c.entities,
           c.content
    FROM c
    WHERE c.status = @status
    """
    params = [{"name": "@status", "value": status}]
    items = container_client.query_items(
        query=query,
        parameters=params,
        enable_cross_partition_query=True
    )
    return list(items)


def get_inputs_count_by_status():
    """Get count of inputs grouped by status from Cosmos DB"""
    query = """
    SELECT c.status, COUNT(1) as count
    FROM c
    GROUP BY c.status
    """
    items = container_client.query_items(
        query=query,
        enable_cross_partition_query=True
    )
    result = {}
    for item in items:
        result[item['status']] = item['count']
    return result


def update_input_status(input_id: str, new_status: str):
    """Update input status in Cosmos DB"""
    try:
        # First get the current item to ensure it exists
        item = container_client.read_item(item=input_id, partition_key=input_id)
        
        # Use replace_item instead of patch_item for better compatibility 
        item['status'] = new_status
        item['last_updated'] = str(datetime.datetime.now())
        
        response = container_client.replace_item(
            item=input_id,
            body=item
        )
        return response
    except cosmos_exceptions.CosmosResourceNotFoundError:
        raise HTTPException(status_code=404, detail="Request ID not found")

# ---------------------------------------------------------------------------- #
#                               API Configuration                              #
# ---------------------------------------------------------------------------- #

app = FastAPI()

# Disable CORS checking
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# ---------------------------------------------------------------------------- #
#                                 API Endpoints                                #
# ---------------------------------------------------------------------------- #


@app.post("/index")
async def index(inputBody: InputBody):
    user_input = inputBody.input
    logger.info(f"Received user input: {user_input}")

    # Create the Input
    input = Input()

    # Generate a uuid for the input
    input.id = str(uuid.uuid4())

    # Update the status
    input.status = "Creating"
    logger.info(f"Creating input: {input.id}")

    # Creation date and last updated date
    input.date = str(datetime.datetime.now())
    input.last_updated = str(datetime.datetime.now())

    # Message for the service bus queue
    message = {
        "request_id": input.id,
        "input": user_input
    }
    logger.info(f"Created message: {message}")

    queue = 'note'
    # If it is a URL
    if user_input.startswith("http"):
        queue = 'website'
        input.title = user_input
        input.source = user_input
        input.type = "Website"
    else:
        title = f"Note [id: {input.id}]"
        input.title = title
        input.source = title
        input.type = "Note"
        input.content = user_input
    logger.info(f"Determined queue: {queue}")

    # Save to Cosmos DB
    save_to_cosmosdb(input)

    # Send the message to the Service Bus
    with ServiceBusClient.from_connection_string(servicebus_connection_string) as client:
        with client.get_queue_sender(queue) as sender:
            # Encode the service bus message dict as JSON string
            message_json = json.dumps(message)
            servicebus_message = ServiceBusMessage(message_json)
            sender.send_messages(servicebus_message)
            # Update the status in Cosmos DB
            update_input_status(input.id, "Queued")

    return {"request_id": input.id}


@app.post("/index_file")
async def upload_file(file: UploadFile = File(...)):
    logger.info('Received file: ' + file.filename)

    # Create the Input
    input = Input()

    # Generate a uuid for the input
    input.id = str(uuid.uuid4())

    # Update the status
    input.status = "Creating"
    logger.info(f"Creating input: {input.id}")

    # Creation date and last updated date
    input.date = str(datetime.datetime.now())
    input.last_updated = str(datetime.datetime.now())

    if (file.filename.lower().endswith(".pdf")):
        queue = 'pdf'
        input.type = "PDF"
    elif (file.filename.lower().endswith(".docx")):
        queue = 'word'
        input.type = "Word"
    elif (file.filename.lower().endswith(".png") or
          file.filename.lower().endswith(".jpg") or
          file.filename.lower().endswith(".jpeg") or
          file.filename.lower().endswith(".gif") or
          file.filename.lower().endswith(".bmp")):
        queue = 'image'
        input.type = "Image"
    else:
        logger.error(f"Unsupported file type.")
        raise HTTPException(status_code=400, detail="Unsupported file type")
    logger.info(f"Determined queue: {queue}")

    logger.info(f"Generated request_id: {input.id}")

    # Upload the file to Azure Blob Storage
    try:
        blob_client = blob_service_client.get_blob_client(
            container=blob_container_name, blob=file.filename)
        blob_client.upload_blob(
            file.file, blob_type="BlockBlob", overwrite=True)
        logger.info(
            f"Uploaded file to Azure Blob Storage: {input.id}_{file.filename}")
    except Exception as e:
        logger.error(f"Error uploading file to Azure Blob Storage: {e}")
        raise HTTPException(
            status_code=500, detail="Error uploading file to Azure Blob Storage")

    input.title = file.filename
    input.source = blob_client.url

    # Save to Cosmos DB
    save_to_cosmosdb(input)

    message = {
        "request_id": input.id,
        "file_name": file.filename,
        "file_container": blob_container_name,
        "file_location": blob_client.url
    }
    logger.info(f"Created message: {message}")

    # Send the message to the Service Bus
    with ServiceBusClient.from_connection_string(servicebus_connection_string) as client:
        with client.get_queue_sender(queue) as sender:
            # Encode the service bus message dict as JSON string
            servicebus_message = ServiceBusMessage(json.dumps(message))
            sender.send_messages(servicebus_message)
            # Update the status in Cosmos DB
            update_input_status(input.id, "Queued")

    return {"request_id": input.id, "file_location": blob_client.url}


@app.get("/status/{request_id}")
async def get_status(request_id: str):
    # Get input from Cosmos DB
    input_item = get_input_by_id_as_dict(request_id)
    
    # If request_id is not found, return HTTP 404
    if not input_item:
        raise HTTPException(status_code=404, detail="Request ID not found")
    
    return {"status": input_item.get("status")}


@app.post("/status/{request_id}")
async def update_status(request_id: str, statusBody: StatusBody):
    # Update status in Cosmos DB
    response = update_input_status(request_id, statusBody.status)
    return {"status": response.get("status")}

@app.post("/inputs/{request_id}/content")
async def update_input_content(request_id: str, content_data: dict):
    """Update the content and metadata of an existing input"""
    try:
        # First get the current item to ensure it exists
        item = container_client.read_item(item=request_id, partition_key=request_id)
        
        # Update content if provided
        if 'content' in content_data:
            item['content'] = content_data['content']
        
        # Update title if provided
        if 'title' in content_data and content_data['title']:
            item['title'] = content_data['title']
        
        # Update description if provided
        if 'description' in content_data and content_data['description']:
            item['description'] = content_data['description']
        
        # Update last_updated timestamp
        item['last_updated'] = str(datetime.datetime.now())
        
        # Use replace_item to update the document
        container_client.replace_item(
            item=request_id,
            body=item
        )
        
        return {"status": "Content updated successfully", "id": request_id}
    except cosmos_exceptions.CosmosResourceNotFoundError:
        raise HTTPException(status_code=404, detail="Request ID not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating content: {str(e)}")


@app.get("/inputs")
async def get_inputs():
    # Get all inputs from Cosmos DB
    inputs = get_all_inputs_as_dict()
    return JSONResponse(content=inputs)


@app.get("/inputs/count")
async def get_inputs_count():
    # Count all inputs in Cosmos DB
    query = "SELECT VALUE COUNT(1) FROM c"
    items = container_client.query_items(
        query=query,
        enable_cross_partition_query=True
    )
    count = next(iter(items))
    return count


@app.get("/inputs/count-by-status")
async def get_inputs_count_by_status_endpoint():
    # Get count of inputs by status from Cosmos DB
    return get_inputs_count_by_status()


@app.get("/inputs/status/{status}")
async def get_inputs_by_status_endpoint(status: str):
    # Get inputs with specific status from Cosmos DB
    return get_inputs_by_status(status)


@app.get("/inputs/status/{status}/count")
async def get_inputs_count_by_status_endpoint(status: str):
    # Count inputs with specific status in Cosmos DB
    query = "SELECT VALUE COUNT(1) FROM c WHERE c.status = @status"
    params = [{"name": "@status", "value": status}]
    items = container_client.query_items(
        query=query,
        parameters=params,
        enable_cross_partition_query=True
    )
    count = next(iter(items))
    return count


@app.get("/inputs/{request_id}")
async def get_input(request_id: str):
    # Get input by ID from Cosmos DB
    input_item = get_input_by_id_as_dict(request_id)
    
    # If request_id is not found, return HTTP 404
    if not input_item:
        raise HTTPException(status_code=404, detail="Request ID not found")
    
    return input_item
