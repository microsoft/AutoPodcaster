import os
import json
import uuid
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
import re

load_dotenv(override=True)

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
            receiver = servicebus_client.get_queue_receiver('note')
            async with receiver:
                received_messages = await receiver.receive_messages(
                    max_message_count=1, max_wait_time=5)
                for message in received_messages:
                    website_input = json.loads(str(message))
                    content = website_input['input']
                    update_status(website_input['request_id'], "Indexing")
                    input = await index_note(content)
                    update_status(website_input['request_id'], "Indexed")
                    save_to_cosmosdb(input)
                    update_status(website_input['request_id'], "Saved")
                    await receiver.complete_message(message)
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


async def index_note(content: str) -> Input:

    # We will generate a title and a description from the content.
    # using OpenAI GPT-4.

    # Create the prompt to generate the title and description.
    prompt_template = """Generate a title (max 8 words) and description (max 3 sentences) for the following content: {content}.
     
    Provide in following format:
    [[Title goes here]]
    $$Description goes here$$
     """
    # Create the gpt-4o model client
    azure_openai_client = AzureOpenAI(
        api_key=os.environ['AZURE_OPENAI_KEY'],
        azure_endpoint=os.environ['AZURE_OPENAI_ENDPOINT'],
        api_version=os.environ['AZURE_OPENAI_API_VERSION']
    )

    # Get first 500 tokens
    prompt = prompt_template.format(content=content[:500])

    corrected_content = azure_openai_client.chat.completions.create(
        model="gpt-4o",
        temperature=0,
        top_p=1,
        messages=[
            {"role": "user", "content": prompt},
        ],
    ).choices[0].message.content

    # Title and description is returned in following format: [[Title goes here]] and $$Description goes here$$
    # Extract the title and description from the corrected content.

    # Extract the title and description from the corrected content.
    title_match = re.search(r'\[\[(.*?)\]\]', corrected_content)
    description_match = re.search(r'\$\$(.*?)\$\$', corrected_content)

    title = title_match.group(1) if title_match else None
    description = description_match.group(1) if description_match else None

    print(f"Title: {title}")
    print(f"Description: {description}")

    # Create a document from the content.
    documents = [Document(page_content=content, metadata={})]

    input = Input()
    input.id = str(uuid.uuid4())
    input.title = title
    input.date = ''
    input.last_updated = ''
    input.author = ''
    input.description = description
    input.source = ''
    input.type = 'note'
    input.thumbnail_url = ''
    input.topics = []
    input.entities = []

    for document in documents:
        document.metadata['id'] = input.id
        document.metadata['title'] = title
        document.metadata['source'] = ''
        document.metadata['description'] = description
        document.metadata['thumbnail_url'] = ''
        document.metadata['type'] = 'note'

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
