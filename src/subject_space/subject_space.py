from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from azure.cosmos import CosmosClient
from langchain_community.vectorstores.azuresearch import AzureSearch
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import AzureOpenAIEmbeddings
from langchain_core.documents.base import Document
import logging
import uuid
import datetime
import os

# Load the environment variables
load_dotenv(override=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
servicebus_connection_string = os.getenv("SERVICEBUS_CONNECTION_STRING")
cosmosdb_connection_string = os.getenv("COSMOSDB_CONNECTION_STRING")
azure_search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
azure_search_admin_key = os.getenv("AZURE_SEARCH_ADMIN_KEY")

class InputSubjectSpace(BaseModel):
    subject: str


class SubjectSpace(BaseModel):
    id: str
    subject: str
    date: str
    last_updated: str
    inputs: list
    index_name: str


app = FastAPI()

# Disable CORS checking
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Define the embeddings model
azure_openai_embeddings = AzureOpenAIEmbeddings(
    api_key=os.environ['AZURE_OPENAI_KEY'],
    azure_endpoint=os.environ['AZURE_OPENAI_ENDPOINT'],
    api_version=os.environ['AZURE_OPENAI_API_VERSION'],
    azure_deployment=os.environ['AZURE_OPENAI_DEPLOYMENT_EMBEDDINGS']
)


@app.get("/subject")
async def get_subjects():
    """Get all subjects in the subject space.
    """
    client = CosmosClient.from_connection_string(cosmosdb_connection_string)
    database = client.get_database_client("autopodcaster")
    container = database.get_container_client("subjects")

    subjects = []

    logger.info("Querying subjects")
    for item in container.query_items(
        query="SELECT * FROM subjects",
        enable_cross_partition_query=True
    ):
        subjects.append(item)

    return subjects


@app.get("/subject/{subject_id}")
async def get_subject(subject_id: str):
    """Get a subject in the subject space.
    """
    client = CosmosClient.from_connection_string(cosmosdb_connection_string)
    database = client.get_database_client("autopodcaster")
    container = database.get_container_client("subjects")

    subject = container.read_item(item=subject_id, partition_key=subject_id)
    return subject


@app.get("/subject/{subject_id}/inputs")
async def get_subject_inputs(subject_id: str):
    """Get all inputs for a subject in the subject space.
    """
    client = CosmosClient.from_connection_string(cosmosdb_connection_string)
    database = client.get_database_client("autopodcaster")
    container = database.get_container_client("subjects")

    subject = container.read_item(item=subject_id, partition_key=subject_id)
    inputs = get_inputs(subject.get('inputs'))
    return inputs


@app.post("/subject")
async def create_subject(inputSubjectSpace: InputSubjectSpace):
    """Create a subject in the subject space.
    """
    logger.info("Creating a subject.")

    client = CosmosClient.from_connection_string(cosmosdb_connection_string)
    database = client.get_database_client("autopodcaster")
    container = database.get_container_client("subjects")

    now_string = datetime.datetime.now().isoformat()

    inputs = retrieve(inputSubjectSpace.subject)

    if len(inputs) == 0:
        raise HTTPException(
            status_code=404, detail="No documents found for the subject")

    id = str(uuid.uuid4())
    index_name = id.replace('-', '')

    create_index(index_name, inputs)

    subject = SubjectSpace(
        id=id,
        subject=inputSubjectSpace.subject,
        date=now_string,
        last_updated=now_string,
        inputs=inputs,
        index_name=index_name
    )

    container.create_item(body=subject.model_dump())
    return subject


@app.put("/subject/{subject_id}")
async def update_subject(subject_id: str, inputSubjectSpace: InputSubjectSpace):
    """Update a subject in the subject space.
    """
    client = CosmosClient.from_connection_string(cosmosdb_connection_string)
    database = client.get_database_client("autopodcaster")
    container = database.get_container_client("subjects")

    subject = container.read_item(item=subject_id, partition_key=subject_id)
    subject.subject = inputSubjectSpace.subject
    subject.last_updated = datetime.datetime.now().isoformat()

    container.upsert_item(body=subject)
    return subject


@app.delete("/subject/{subject_id}")
async def delete_subject(subject_id: str):
    """Delete a subject in the subject space.
    """
    client = CosmosClient.from_connection_string(cosmosdb_connection_string)
    database = client.get_database_client("autopodcaster")
    container = database.get_container_client("subjects")

    container.delete_item(item=subject_id, partition_key=subject_id)
    return {"message": "Subject deleted"}


def get_inputs(ids):
    """Get all inputs for a subject in the subject space.
    """
    id_list = ', '.join([f'\"{id}\"' for id in ids])
    query = f"SELECT * FROM c WHERE c.id IN ({id_list})"
    client = CosmosClient.from_connection_string(cosmosdb_connection_string)
    database = client.get_database_client("autopodcaster")
    container = database.get_container_client("inputs")
    inputs = container.query_items(
        query=query,
        enable_cross_partition_query=True
    )
    inputs_list = []
    for input in inputs:
        inputs_list.append(input)
    return inputs_list


def retrieve(subject: str):
    vector_store = AzureSearch(
        azure_search_endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
        azure_search_key=os.getenv("AZURE_SEARCH_ADMIN_KEY"),
        index_name="knowledgebase",
        embedding_function=azure_openai_embeddings.embed_query,
    )
    results = vector_store.similarity_search_with_relevance_scores(
        query=subject, k=100, score_threshold=0.55)
    # Create a list of unique ids from the results
    unique_ids = []
    for result in results:
        metadata = result[0].metadata
        id = metadata['id']
        print(f"Title: {metadata['title']} - Score: {result[1]}")
        if id not in unique_ids:
            unique_ids.append(id)

    return unique_ids


def create_index(index_name, input_ids):
    inputs = get_inputs(input_ids)
    documents = []
    for input in inputs:
        document = Document(
            page_content=input['content'],
            metadata={
                "id": input['id'],
                "title": input['title'],
                "source": input['source'],
                "description": input['description'],
                "thumbnail_url": input['thumbnail_url'],
                "page": 0,
                "type": input['type']
            }
        )
        documents.append(document)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    splits = text_splitter.split_documents(documents)
    vector_store = AzureSearch(
        azure_search_endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
        azure_search_key=os.getenv("AZURE_SEARCH_ADMIN_KEY"),
        index_name=index_name,
        embedding_function=azure_openai_embeddings.embed_query,
    )
    vector_store.add_documents(documents=splits)
