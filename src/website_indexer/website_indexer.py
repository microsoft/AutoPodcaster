import os
import json
import requests
import asyncio
from dotenv import load_dotenv
from azure.servicebus.aio import ServiceBusClient
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores.azuresearch import AzureSearch
from langchain_community.document_loaders import AsyncHtmlLoader
from bs4 import BeautifulSoup

load_dotenv()

servicebus_connection_string = os.getenv("SERVICEBUS_CONNECTION_STRING")
status_endpoint = os.getenv("STATUS_ENDPOINT")

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
                    request_id = website_input['request_id']
                    
                    # Update status to "Indexing" through API
                    update_status(request_id, "Indexing")
                    await receiver.complete_message(message)
                    
                    # Process the website and get content/metadata
                    processed_content = await index_website(website_url)
                    
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


async def index_website(website_url: str) -> dict:
    """Process website and return a dictionary with content and metadata"""
    loader = AsyncHtmlLoader(website_url)
    documents = loader.load()

    content = documents[0].page_content

    # Parse the title and description from the HTML
    soup = BeautifulSoup(content, 'html.parser')
    title = soup.title.string if soup.title else 'Unknown Title'
    
    # Try to get description from meta tags
    description = ''
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc and meta_desc.get('content'):
        description = meta_desc.get('content')
    else:
        # Fallback to og:description
        og_desc = soup.find('meta', attrs={'property': 'og:description'})
        if og_desc and og_desc.get('content'):
            description = og_desc.get('content')

    for document in documents:
        document.metadata['title'] = title
        document.metadata['source'] = website_url
        document.metadata['description'] = description
        document.metadata['thumbnail_url'] = ''
        document.metadata['type'] = 'website'

        # Extract the content from HTML tags
        page_content = document.page_content
        new_content = ""
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(page_content, 'html.parser')
        
        # Extract headings
        headings = []
        for tag in ['h1', 'h2', 'h3']:
            headings.extend([h.get_text(strip=True) for h in soup.find_all(tag)])
        if headings:
            new_content += '\n\n'.join(headings) + '\n\n'

        # Extract paragraphs
        paragraphs = [p.get_text(strip=True) for p in soup.find_all('p')]
        if paragraphs:
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

    extracted_content = '\n\n'.join([doc.page_content for doc in documents])

    # Return the processed content and metadata
    return {
        'content': extracted_content,
        'title': title,
        'description': description
    }


while (True):
    asyncio.run(main())
