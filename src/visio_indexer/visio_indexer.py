import os
import io
import uuid
import json
import requests
import asyncio
from dotenv import load_dotenv
from azure.servicebus.aio import ServiceBusClient
from azure.cosmos import CosmosClient
from openai import AzureOpenAI
from langchain_core.documents.base import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores.azuresearch import AzureSearch
from PIL import Image
import pyvisio

# Load the environment variables
load_dotenv()

servicebus_connection_string = os.getenv("SERVICEBUS_CONNECTION_STRING")
cosmosdb_connection_string = os.getenv("COSMOSDB_CONNECTION_STRING")
status_endpoint = os.getenv("STATUS_ENDPOINT")

class Input:
    id: str
    title: str
    date: str
    last_updated: str
    author: str
    description: str
    source: str
    type: str
    thumbnail_url: str
    topics: list
    entities: list
    content: str

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "date": self.date,
            "last_updated": self.last_updated,
            "author": self.author,
            "description": self.description,
            "source": self.source,
            "type": self.type,
            "thumbnail_url": self.thumbnail_url,
            "topics": self.topics,
            "entities": self.entities,
            "content": self.content
        }

async def main():
    """Index a Visio diagram in the vector store."""
    async with ServiceBusClient.from_connection_string(
            conn_str=servicebus_connection_string) as servicebus_client:
        async with servicebus_client:
            receiver = servicebus_client.get_queue_receiver('visio')
            async with receiver:
                received_messages = await receiver.receive_messages(
                    max_message_count=1, max_wait_time=5)
                for message in received_messages:
                    visio_input = json.loads(str(message))
                    visio_url = visio_input['input']
                    update_status(visio_input['request_id'], "Indexing")
                    input = index_visio(visio_url)
                    update_status(visio_input['request_id'], "Indexed")
                    save_to_cosmosdb(input)
                    update_status(visio_input['request_id'], "Saved")
                    await receiver.complete_message(message)

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

def index_visio(visio_url: str):
    visio_file = requests.get(visio_url).content
    visio = pyvisio.VisioFile(io.BytesIO(visio_file))

    title = visio.title
    description = visio.description
    url = visio_url

    input = Input()
    input.id = str(uuid.uuid4())
    input.title = title
    input.date = visio.creation_date.isoformat()
    input.last_updated = visio.last_modified_date.isoformat()
    input.author = visio.author
    input.description = description
    input.source = url
    input.type = 'visio'
    input.thumbnail_url = ''
    input.topics = []
    input.entities = []

    # Convert Visio to image
    image = visio.pages[0].render()
    image_file_name = f"{input.id}.png"
    image.save(image_file_name)

    # Create the prompt to generate description using GPT-4
    prompt_template = """Given the title and description of a Visio diagram, generate a detailed description of the diagram.

    Title: {title}
    Description:
    {description}
    """

    # Create the gpt-4 model client
    azure_openai_client = AzureOpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        azure_endpoint=os.environ['OPENAI_AZURE_ENDPOINT'],
        api_version=os.environ['OPENAI_API_VERSION']
    )

    encoding_name = 'gpt-4'

    prompt = prompt_template.format(
        title=title, description=description)
    generated_description = azure_openai_client.chat.completions.create(
        model="gpt-4",
        temperature=0,
        top_p=1,
        messages=[
            {"role": "user", "content": prompt},
        ],
    ).choices[0].message.content

    input.content = generated_description

    # Create langchain document
    document = Document(
        page_content=generated_description,
        metadata={
            "title": title,
            "source": url,
            "description": description,
            "thumbnail_url": '',
            "page": 0,
            "type": "visio"
        }
    )

    documents = [document]  # List of documents to be processed

    # Split the document in chunks of maximum 1000 characters with 200 characters overlap using langchain
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    splits = text_splitter.split_documents(documents)

    # Define the embeddings model
    azure_openai_embeddings = AzureOpenAIEmbeddings(
        api_key=os.environ['OPENAI_API_KEY'],
        azure_endpoint=os.environ['OPENAI_AZURE_ENDPOINT'],
        api_version=os.environ['OPENAI_API_VERSION'],
        azure_deployment=os.environ['OPENAI_AZURE_DEPLOYMENT_EMBEDDINGS']
    )

    # Create the vector store
    index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")
    vector_store = AzureSearch(
        azure_search_endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
        azure_search_key=os.getenv("AZURE_SEARCH_ADMIN_KEY"),
        index_name=index_name,
        embedding_function=azure_openai_embeddings.embed_query,
    )
    vector_store.add_documents(documents=splits)

    return input

while (True):
    asyncio.run(main())
    asyncio.sleep(5)
