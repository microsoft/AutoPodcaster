import os
import json
import uuid
import requests
import asyncio
from dotenv import load_dotenv
from azure.servicebus.aio import ServiceBusClient
from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores.azuresearch import AzureSearch
from langchain_community.document_loaders import PyPDFLoader
import tiktoken
import time

from autopodcaster_model import Input

load_dotenv(override=True)

servicebus_connection_string = os.getenv("SERVICEBUS_CONNECTION_STRING")
cosmosdb_connection_string = os.getenv("COSMOSDB_CONNECTION_STRING")
status_endpoint = os.getenv("STATUS_ENDPOINT")
blob_service_client = BlobServiceClient.from_connection_string(
    os.getenv("STORAGE_CONNECTION_STRING"))
container_name = "uploads"


async def main():
    async with ServiceBusClient.from_connection_string(
            conn_str=servicebus_connection_string) as servicebus_client:
        async with servicebus_client:
            receiver = servicebus_client.get_queue_receiver('pdf')
            async with receiver:
                received_messages = await receiver.receive_messages(
                    max_message_count=1, max_wait_time=5)
                for message in received_messages:
                    print(str(message))
                    pdf_input = json.loads(str(message))
                    file_location = pdf_input['file_name']
                    update_status(pdf_input['request_id'], "Indexing")
                    await receiver.complete_message(message)
                    input = index_pdf(file_location)
                    update_status(pdf_input['request_id'], "Indexed")
                    save_to_cosmosdb(input)
                    update_status(pdf_input['request_id'], "Saved")


def save_to_cosmosdb(input: Input):
    client = CosmosClient.from_connection_string(cosmosdb_connection_string)
    database_name = "autopodcaster"
    database = client.get_database_client(database_name)
    container_name = "inputs"
    container = database.get_container_client(container_name)
    container.create_item(body=input.to_dict())


def update_status(request_id: str, status: str):
    status = {"status": status}
    requests.post(
        f"{status_endpoint}/status/{request_id}", json=status)


def num_tokens_from_string(string: str, encoding_name: str) -> int:
    encoding = tiktoken.encoding_for_model(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens


def index_pdf(file_location: str):
    blob_client = blob_service_client.get_blob_client(
        container=container_name, blob=file_location)
    download_file_path = get_file(file_location)
    with open(download_file_path, "wb") as download_file:
        download_file.write(blob_client.download_blob().readall())

    loader = PyPDFLoader(download_file_path)
    documents = loader.load()

    title = documents[0].metadata.get('title', 'Unknown Title')
    description = documents[0].metadata.get('description', '')
    url = file_location

    input = Input()
    input.id = str(uuid.uuid4())
    input.title = title
    input.date = ''
    input.last_updated = ''
    input.status = ''
    input.author = ''
    input.description = description
    input.source = url
    input.type = 'pdf'
    input.thumbnail_url = ''
    input.topics = []
    input.entities = []

    for document in documents:
        # For Azure Search each document needs a different id
        # and each chunk too => do not set the id here or
        # only 1 input or chunk of the input will be indexed
        document.metadata['input_id'] = input.id
        document.metadata['title'] = title
        document.metadata['source'] = url
        document.metadata['description'] = description
        document.metadata['thumbnail_url'] = ''
        # page metadata is added by PyPDFLoader
        document.metadata['type'] = 'pdf'

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    splits = text_splitter.split_documents(documents)

    azure_openai_embeddings = AzureOpenAIEmbeddings(
        api_key=os.environ['AZURE_OPENAI_KEY'],
        azure_endpoint=os.environ['AZURE_OPENAI_ENDPOINT'],
        api_version=os.environ['AZURE_OPENAI_API_VERSION'],
        azure_deployment=os.environ['AZURE_OPENAI_DEPLOYMENT_EMBEDDINGS']
    )

    index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")
    if index_name is None or index_name == "":
        index_name = "knowledgebase"

    vector_store = AzureSearch(
        azure_search_endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
        azure_search_key=os.getenv("AZURE_SEARCH_ADMIN_KEY"),
        index_name=index_name,
        embedding_function=azure_openai_embeddings.embed_query,
        additional_search_client_options={"retry_total": 20},
    )
    # Add documents by batch of 500 as there is a limit of 1000 documents per request
    # and 16MB per request
    num_splits = len(splits)
    batch_size = 500
    for i in range(0, num_splits, batch_size):
        splits_batch = splits[i:i+batch_size]
        print(
            f"Adding batch {i} to {i+batch_size} of {num_splits} with {len(splits_batch)} documents")
        vector_store.add_documents(documents=splits_batch)
        time.sleep(30)

    input.content = '\n\n'.join([doc.page_content for doc in documents])

    os.remove(download_file_path)

    return input


def get_file(file_name: str):
    """Get file path

    Args:
        file_name (str): File name

    Returns:
        File path
    """
    output_folder = 'outputs'
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    return os.path.join(output_folder, file_name)


while (True):
    asyncio.run(main())
    asyncio.sleep(5)
