import os
import json
import requests
import asyncio
from dotenv import load_dotenv
from azure.servicebus.aio import ServiceBusClient
from azure.storage.blob import BlobServiceClient
from openai import AzureOpenAI
from langchain_core.documents.base import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores.azuresearch import AzureSearch
import tiktoken
import re
import base64

load_dotenv(override=True)

servicebus_connection_string = os.getenv("SERVICEBUS_CONNECTION_STRING")
status_endpoint = os.getenv("STATUS_ENDPOINT")
blob_service_client = BlobServiceClient.from_connection_string(
    os.getenv("STORAGE_CONNECTION_STRING"))
container_name = "uploads"


async def main():
    async with ServiceBusClient.from_connection_string(
            conn_str=servicebus_connection_string) as servicebus_client:
        async with servicebus_client:
            receiver = servicebus_client.get_queue_receiver('image')
            async with receiver:
                received_messages = await receiver.receive_messages(
                    max_message_count=1, max_wait_time=5)
                for message in received_messages:
                    image_input = json.loads(str(message))
                    image_location = image_input['file_name']
                    request_id = image_input['request_id']
                    
                    # Update status to "Indexing" through API
                    update_status(request_id, "Indexing")
                    await receiver.complete_message(message)
                    
                    # Process the image and get content/metadata
                    processed_content = await index_image(image_location)
                    
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


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


async def index_image(image_location: str) -> dict:
    """Process image and return a dictionary with content and metadata"""
    blob_client = blob_service_client.get_blob_client(
        container=container_name, blob=image_location)
    download_file_path = get_file(image_location)
    with open(download_file_path, "wb") as download_file:
        download_file.write(blob_client.download_blob().readall())

    base64_image = encode_image(download_file_path)

    # Create the prompt to generate the title and description.
    prompt_template = """Get the content from the image and generate a title, short description (4 sentences) and full text for the content.
       
    Provide in following format:
    [[Title goes here]]
    $$Description goes here$$
    ((Full text goes here))

    """

    # Create the gpt-4o model client
    azure_openai_client = AzureOpenAI(
        api_key=os.environ['AZURE_OPENAI_KEY'],
        azure_endpoint=os.environ['AZURE_OPENAI_ENDPOINT'],
        api_version=os.environ['AZURE_OPENAI_API_VERSION']
    )

    corrected_content = azure_openai_client.chat.completions.create(
        model="gpt-4o",
        temperature=0,
        top_p=1,
        messages=[
            {"role": "user", "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}"
                    }
                },
                {
                    "type": "text",
                    "text": prompt_template
                }
            ]},
        ],
    ).choices[0].message.content
    print(f"Corrected content: {corrected_content}")

    # Remove the line breaks from the corrected content.
    corrected_content = corrected_content.replace('\n', ' ')

    # Title and description is returned in following format: [[Title goes here]] and $$Description goes here$$ and ((Full text goes here))
    # Extract the title and short description and description from the corrected content.
    title_match = re.search(r'\[\[(.*?)\]\]', corrected_content)
    description_match = re.search(r'\$\$(.*?)\$\$', corrected_content)
    full_text_match = re.search(r'\(\((.*?)\)\)', corrected_content)

    title = title_match.group(1) if title_match else None
    description = description_match.group(1) if description_match else None
    full_text = full_text_match.group(1) if full_text_match else None

    print(f"Title: {title}")
    print(f"Description: {description}")
    print(f"Full text: {full_text}")

    # Create a document from the content.
    documents = [Document(page_content="", metadata={})]

    # Setup document metadata for Azure Search
    for document in documents:
        document.metadata['title'] = title
        document.metadata['source'] = ''
        document.metadata['description'] = description
        document.metadata['thumbnail_url'] = ''
        document.metadata['page'] = -1
        document.metadata['type'] = 'note'
        document.page_content = full_text

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

    content = '\n\n'.join([doc.page_content for doc in documents])

    os.remove(download_file_path)

    # Return the processed content and metadata
    return {
        'content': content,
        'title': title,
        'description': description
    }


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


def num_tokens_from_string(string: str, encoding_name: str) -> int:
    encoding = tiktoken.encoding_for_model(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens


while (True):
    asyncio.run(main())