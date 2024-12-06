from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from azure.cosmos import CosmosClient

import requests
import os
import uuid
import json
import logging


class InputBody(BaseModel):
    subject_id: str
    output_type: str


class StatusBody(BaseModel):
    status: str


load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

servicebus_connection_string = os.getenv("SERVICEBUS_CONNECTION_STRING")
cosmosdb_connection_string = os.getenv("COSMOSDB_CONNECTION_STRING")
subject_space_api_url = os.getenv("SUBJECT_SPACE_API_URL")

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


@app.post("/output")
async def generate_output(inputBody: InputBody):
    subject_id = inputBody.subject_id
    output_type = inputBody.output_type
    logger.info(
        f"Received subject_id: {subject_id}, output_type: {output_type}")

    # Generate a uuid for the request
    request_id = str(uuid.uuid4())
    status_cache[request_id] = "Creating"
    logger.info(f"Generated request_id: {request_id}")

    message = {
        "request_id": request_id,
        "subject_id": subject_id,
        "output_type": output_type
    }
    logger.info(f"Created message: {message}")

    queue = output_type
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

    return message


@app.get("/output/for-subject/{subject_id}")
async def get_output_for_subject(subject_id: str):
    # Use Cosmos DB to fetch the output for the subject
    client = CosmosClient.from_connection_string(cosmosdb_connection_string)
    database = client.get_database_client("autopodcaster")
    container = database.get_container_client("outputs")

    # Query the Cosmos DB container for the output
    query = f"SELECT * FROM c WHERE c.subject_id = '{subject_id}'"
    ouputs_iterator = container.query_items(
        query=query, enable_cross_partition_query=True)
    outputs = []
    for output in ouputs_iterator:
        outputs.append(output)
    return outputs


@app.get("/status/{request_id}")
async def get_status(request_id: str):
    # If request_id is not found, return HTTP 404
    if request_id not in status_cache:
        raise HTTPException(status_code=404, detail="Request ID not found")
    return {"status": status_cache.get(request_id)}


@app.post("/status/{request_id}")
async def update_status(request_id: str, statusBody: StatusBody):
    status_cache[request_id] = statusBody.status
    return {"status": status_cache[request_id]}
