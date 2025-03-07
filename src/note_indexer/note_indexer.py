import os
import json
import requests
import asyncio
from dotenv import load_dotenv
from azure.servicebus.aio import ServiceBusClient
from openai import AzureOpenAI
from langchain_core.documents.base import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores.azuresearch import AzureSearch
import re

load_dotenv(override=True)

servicebus_connection_string = os.getenv("SERVICEBUS_CONNECTION_STRING")
status_endpoint = os.getenv("STATUS_ENDPOINT")


async def main():
    async with ServiceBusClient.from_connection_string(
            conn_str=servicebus_connection_string) as servicebus_client:
        async with servicebus_client:
            receiver = servicebus_client.get_queue_receiver('note')
            async with receiver:
                received_messages = await receiver.receive_messages(
                    max_message_count=1, max_wait_time=5)
                for message in received_messages:
                    note_input = json.loads(str(message))
                    content = note_input['input']
                    request_id = note_input['request_id']
                    
                    # Update status to "Indexing" through API
                    update_status(request_id, "Indexing")
                    await receiver.complete_message(message)
                    
                    # Process the note and get content/metadata
                    processed_content = await index_note(content)
                    
                    # Send the processed content to api_input to update the record
                    send_content_to_api(request_id, processed_content)
                    
                    # Update status to "Indexed" through API
                    update_status(request_id, "Indexed")
    asyncio.sleep(5)


def update_status(request_id: str, status: str):
    """Update the status of a document through the API"""
    status_data = {"status": status}
    try:
        response = requests.post(
            f"{status_endpoint}/status/{request_id}", json=status_data)
        response.raise_for_status()
        print(f"Successfully updated status to '{status}' for request {request_id}")
    except requests.exceptions.RequestException as e:
        print(f"Error updating status for request {request_id}: {e}")


def send_content_to_api(request_id: str, processed_content: dict):
    """Send the processed content to api_input to update the record"""
    try:
        # Use the content update endpoint with a simple dictionary
        response = requests.post(
            f"{status_endpoint}/inputs/{request_id}/content", 
            json=processed_content
        )
        response.raise_for_status()
        print(f"Successfully sent processed content to API for request {request_id}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending content to API for request {request_id}: {e}")


async def index_note(content: str) -> dict:
    """Process note content and return a dictionary with enhanced content and metadata"""
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
    title_match = re.search(r'\[\[(.*?)\]\]', corrected_content)
    description_match = re.search(r'\$\$(.*?)\$\$', corrected_content)

    title = title_match.group(1) if title_match else None
    description = description_match.group(1) if description_match else None

    print(f"Title: {title}")
    print(f"Description: {description}")

    # Create a document from the content.
    documents = [Document(page_content=content, metadata={})]

    # Setup document metadata for Azure Search
    for document in documents:
        document.metadata['title'] = title
        document.metadata['source'] = ''
        document.metadata['description'] = description
        document.metadata['thumbnail_url'] = ''
        document.metadata['page'] = -1
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

    # Return the processed content and metadata
    return {
        'content': content,  # Using the original content since it's already text
        'title': title,
        'description': description
    }


while (True):
    asyncio.run(main())