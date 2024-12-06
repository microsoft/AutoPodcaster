import os
import json
import uuid
import requests
import asyncio
from dotenv import load_dotenv
from azure.servicebus.aio import ServiceBusClient
from azure.cosmos import CosmosClient
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores.azuresearch import AzureSearch
from langchain_community.document_loaders import AsyncHtmlLoader
from bs4 import BeautifulSoup

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
    async with ServiceBusClient.from_connection_string(
            conn_str=servicebus_connection_string) as servicebus_client:
        async with servicebus_client:
            receiver = servicebus_client.get_queue_receiver('website')
            async with receiver:
                received_messages = await receiver.receive_messages(
                    max_message_count=1, max_wait_time=5)
                for message in received_messages:
                    website_input = json.loads(str(message))
                    website_url = website_input['input']
                    update_status(website_input['request_id'], "Indexing")
                    await receiver.complete_message(message)
                    input = await index_website(website_url)
                    update_status(website_input['request_id'], "Indexed")
                    save_to_cosmosdb(input)
                    update_status(website_input['request_id'], "Saved")
    asyncio.sleep(5)


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


async def index_website(website_url: str) -> Input:

    loader = AsyncHtmlLoader(website_url)
    documents = loader.load()

    content = documents[0].page_content

    # Parse the title and description from the HTML
    soup = BeautifulSoup(content, 'html.parser')
    title = soup.title.string if soup.title else 'Unknown Title'
    description = soup.description.string if soup.description else ''

    input = Input()
    input.id = str(uuid.uuid4())
    input.title = title
    input.date = ''
    input.last_updated = ''
    input.author = ''
    input.description = description
    input.source = website_url
    input.type = 'website'
    input.thumbnail_url = ''
    input.topics = []
    input.entities = []

    for document in documents:
        document.metadata['id'] = input.id
        document.metadata['title'] = title
        document.metadata['source'] = website_url
        document.metadata['description'] = description
        document.metadata['thumbnail_url'] = ''
        document.metadata['type'] = 'website'

        # We will extract the correct information from the html tags.
        page_content = document.page_content

        new_content = ""
        # Extract headings
        soup = BeautifulSoup(page_content, 'html.parser')
        h1 = [h1.get_text(strip=True) for h1 in soup.find_all('h1')]
        new_content += '\n\n'.join(h1)
        h2 = [h2.get_text(strip=True) for h2 in soup.find_all('h2')]
        new_content += '\n\n'.join(h2)
        h3 = [h3.get_text(strip=True) for h3 in soup.find_all('h3')]
        new_content += '\n\n'.join(h3)

        # Extract paragraphs
        soup = BeautifulSoup(page_content, 'html.parser')
        paragraphs = [p.get_text(strip=True) for p in soup.find_all('p')]
        new_content += '\n\n'.join(paragraphs)

        document.page_content = new_content

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
    )
    vector_store.add_documents(documents=splits)

    input.content = '\n\n'.join([doc.page_content for doc in documents])

    return input

while (True):
    asyncio.run(main())
