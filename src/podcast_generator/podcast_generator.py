from dotenv import load_dotenv
from azure.servicebus.aio import ServiceBusClient
from azure.cosmos import CosmosClient
from openai import AzureOpenAI
from langchain_openai import AzureOpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI
from langchain_community.vectorstores.azuresearch import AzureSearch
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
import azure.cognitiveservices.speech as speechsdk
import json
from azure.storage.blob import BlobServiceClient
import datetime
import os
import json
import uuid
import requests
import asyncio

load_dotenv(override=True)

servicebus_connection_string = os.getenv("SERVICEBUS_CONNECTION_STRING")
cosmosdb_connection_string = os.getenv("COSMOSDB_CONNECTION_STRING")
output_status_endpoint = os.getenv("OUTPUT_STATUS_ENDPOINT")
blob_service_client = BlobServiceClient.from_connection_string(
    os.getenv("STORAGE_CONNECTION_STRING"))
container_name = "downloads"
downloads_sas_token = os.getenv("DOWNLOADS_SAS_TOKEN")
subject_space_endpoint = os.getenv("SUBJECT_SPACE_ENDPOINT")

# Define the embeddings model
azure_openai_embeddings = AzureOpenAIEmbeddings(
        api_key=os.environ['AZURE_OPENAI_KEY'],
        azure_endpoint=os.environ['AZURE_OPENAI_ENDPOINT'],
        api_version=os.environ['AZURE_OPENAI_API_VERSION'],
        azure_deployment=os.environ['AZURE_OPENAI_DEPLOYMENT_EMBEDDINGS']
)


class Output:
    id: str
    type: str
    created_at: str
    last_updated: str
    url: str
    subject_id: str
    outline: str
    content: str
    ssml: str

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "url": self.url,
            "subject_id": self.subject_id,
            "outline": self.outline,
            "content": self.content,
            "ssml": self.ssml
        }


async def main():
    async with ServiceBusClient.from_connection_string(
            conn_str=servicebus_connection_string) as servicebus_client:
        async with servicebus_client:
            receiver = servicebus_client.get_queue_receiver('podcast')
            async with receiver:
                received_messages = await receiver.receive_messages(
                    max_message_count=1, max_wait_time=5)
                for message in received_messages:
                    podcast_input = json.loads(str(message))
                    subject_id = podcast_input['subject_id']
                    update_status(podcast_input['request_id'], "Processing")
                    await receiver.complete_message(message)
                    output = process_podcast(subject_id)
                    update_status(podcast_input['request_id'], "Processed")
                    save_to_cosmosdb(output)
                    update_status(podcast_input['request_id'], "Saved")


def save_to_cosmosdb(output: Output):
    client = CosmosClient.from_connection_string(cosmosdb_connection_string)
    database_name = "autopodcaster"
    database = client.get_database_client(database_name)
    container_name = "outputs"
    container = database.get_container_client(container_name)
    container.create_item(body=output.to_dict())


def update_status(request_id: str, status: str):
    status = {"status": status}
    requests.post(
        f"{output_status_endpoint}/status/{request_id}", json=status)


def process_podcast(subject_id: str) -> Output:
    response = requests.get(f"{subject_space_endpoint}/subject/{subject_id}")
    if response.status_code != 200:
        raise Exception("Subject not found")
    subject_json = response.json()

    subject = subject_json.get('subject', '')
    input_ids = subject_json.get('inputs', '')
    index_name = subject_json.get('index_name', '')

    output = Output()
    output.id = str(uuid.uuid4())
    output.subject_id = subject_id
    output.type = "podcast"
    output.created_at = datetime.datetime.now().isoformat()
    output.last_updated = output.created_at
    output.url = ''

    system_prompt = (
        "You are an assistant for question-answering tasks. "
        "Use the following pieces of retrieved context to answer "
        "the question. If you don't know the answer, say that you "
        "don't know. Use three sentences maximum and keep the "
        "answer concise."
        "\n\n"
        "{context}"
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{input}"),
        ]
    )

    llm = AzureChatOpenAI(
        api_key=os.environ['AZURE_OPENAI_KEY'],
        azure_endpoint=os.environ['AZURE_OPENAI_ENDPOINT'],
        api_version=os.environ['AZURE_OPENAI_API_VERSION'],
        azure_deployment=os.environ['AZURE_OPENAI_DEPLOYMENT'],
        temperature=0,
        top_p=1
    )

    vector_store = AzureSearch(
        azure_search_endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
        azure_search_key=os.getenv("AZURE_SEARCH_ADMIN_KEY"),
        index_name=index_name,
        embedding_function=azure_openai_embeddings.embed_query,
    )

    # GENERATE OUTLINE

    # TODO add the filtering here
    retriever = vector_store.as_retriever()

    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)

    podcast_outline_response = rag_chain.invoke(
        {"input": "Create an outline for a podcast on the following subject: " + subject + "."})
    podcast_outline = podcast_outline_response['answer']
    print(podcast_outline)
    output.outline = podcast_outline

    # GENERATE SCRIPT

    podcast_prompt = f"""Create a podcast complete text based on the following reference outline document:

    {podcast_outline}

    This outline document comes from a video or other media document. Your role is to create the text covering the same topics as the reference document. This text will be used to generate the audio of the podcast. There are 2 participants in the podcast: the host and the cohost. The host will introduce the podcast and the guest. The cohost will explain the outline of the podcast. The host will ask questions to the cohost and the cohost will answer them. The host will thank the audience and close the podcast.
    The name of the host is Bill and his role is to be the listener's podcast assistant. The name of the cohost is Melinda and her role is to be the expert in the podcast topic. The name of the podcast is "Advanced AI Podcast".

    When you thanks someone, write "Thank you" and the name of the person without a comma. For example, "Thank you Bill".

    Output as a JSON with the following fields:
    - title: Title of the podcast
    - intonation: 
    If the host Bill is speaking the intonation can be one of these values:  ["Default", "Angry","Cheerful","Excited","Friendly","Hopeful","Sad","Shouting","Terrified","Unfriendly","Whispering"]
    If the cohost Melinda is speaking the intonation can be one of these: ["Default","Chat","Customer service","Narration - professional","Newscast - casual","Newscast - formal","Cheerful","Empathetic","Angry","Sad","Excited","Friendly","Terrified","Shouting","Unfriendly","Whispering","Hopeful"] 
    - text: an array of objects with the speaker, the intonation and the text to be spoken
    Return only the json as plain text.
    """

    formatted_podcast_prompt = podcast_prompt.format(podcast_outline)
    podcast_script_response = rag_chain.invoke(
        {"input": formatted_podcast_prompt})
    podcast_script_text = str(podcast_script_response['answer']).replace(
        "```json", "").replace("```", "")
    print(podcast_script_text)
    output.content = podcast_script_text

    ssml_script = generate_ssml_script(podcast_script_text)
    output.ssml = ssml_script
    print(ssml_script)

    blob_url_with_sas = generate_podcast_audio(output.id, ssml_script)
    output.url = blob_url_with_sas

    return output


Jason_styles = ["Default", "Angry", "Cheerful", "Excited", "Friendly",
                "Hopeful", "Sad", "Shouting", "Terrified", "Unfriendly", "Whispering"]
Aria_styles = ["Default", "Chat", "Customer service", "Narration - professional", "Newscast - casual", "Newscast - formal",
               "Cheerful", "Empathetic", "Angry", "Sad", "Excited", "Friendly", "Terrified", "Shouting", "Unfriendly", "Whispering", "Hopeful"]


def add_ssml_and_style(line, line_style):
    azure_openai_client = AzureOpenAI(
        api_key=os.environ['AZURE_OPENAI_KEY'],
        azure_endpoint=os.environ['AZURE_OPENAI_ENDPOINT'],
        api_version=os.environ['AZURE_OPENAI_API_VERSION']
    )
    prompt_template = """Given following text and its entonation, rewrite the text with SSML
    Text: {text}
    Intonation:
    {intonation}
    You can use the intonation to add the style to the text as in this example:
    '''<mstts:express-as style="Excited" styledegree="1">Hello everyone!</mstts:express-as>'''
    The styledegree can go from 0.01 to 2
    Note that you do not need to add the "<speak> and <voice> tags. 
    Do not change the pitch.
    Keep the rate always to medium
    ONLY return the imrpoved modified text!!

    You should NEVER include in your ouput this: ```xml

    To be sure write your output as plain text and never as a code snippet.
    
    Here are examples of output you should give:

    Example output 1:
    <mstts:express-as style="Friendly" styledegree="1.5">Welcome to the Advanced AI Podcast. I'm your host, Bill, and today we're diving into the fascinating world of LoRa and LoRaWAN. Joining me is our expert cohost, Melinda, who will help us understand the differences and applications of these technologies.</mstts:express-as>


    Example output 2:
    <mstts:express-as style="professional" styledegree="1">Thank you Bill. In today's episode, we'll explore what LoRa and LoRaWAN are, their key features, and how they differ. We'll also discuss their certifications, real-world applications, and future trends.</mstts:express-as>
    """
    prompt = prompt_template.format(text=line, intonation=line_style)
    system_p = "You are an expert in SSML. You will be given a text and an intonation and you will have to return the same text improved with SSML. Don't forget to escape special characters for XML."
    result = azure_openai_client.chat.completions.create(
        model="gpt-4o",
        temperature=0,
        top_p=1,
        messages=[
            {"role": "system", "content": system_p},
            {"role": "user", "content": prompt},
        ]).choices[0].message.content
    return result


def generate_ssml_script(podcast_script_text):
    podcast_script_json = json.loads(str(podcast_script_text))
    ssml_text = "<speak version='1.0' xmlns:mstts='https://www.w3.org/2001/mstts' xml:lang='en-US'>"
    for line in podcast_script_json['text']:
        speaker = line['speaker']
        text = line['text']
        if speaker == 'Bill':

            ssml_text += f"<voice name='en-US-AndrewMultilingualNeural'>{add_ssml_and_style(line['text'], line['intonation'])}</voice>"

        else:
            ssml_text += f"<voice name='en-US-AriaNeural'>{add_ssml_and_style(line['text'], line['intonation'])}</voice>"
    ssml_text += "</speak>"
    return ssml_text


def generate_podcast_audio(id, ssml_script):
    speech_key = os.getenv("AZURE_SPEECH_KEY")
    service_region = os.getenv("AZURE_SPEECH_REGION")

    retry = 1
   
    while retry <= 3:
        speech_config = speechsdk.SpeechConfig(
            subscription=speech_key, region=service_region)

        speech_synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config)

        result = speech_synthesizer.speak_ssml_async(ssml_script).get()
        stream = speechsdk.AudioDataStream(result)
        id_without_hyphens = str(id).replace("-", "")
        podcast_filename = f"{id_without_hyphens}.wav"
        stream.save_to_wav_file(get_file(podcast_filename))

        print(stream.status)
        
        blob_url_with_sas = write_to_blob(podcast_filename)
        return blob_url_with_sas

        retry += 1
    return ""

def write_to_blob(file_name: str):
    blob_client = blob_service_client.get_blob_client(
        container=container_name, blob=file_name)
    with open(get_file(file_name), "rb") as data:
        result = blob_client.upload_blob(
            data, blob_type="BlockBlob", overwrite=True)
    blob_url_with_sas = f"{blob_client.url}?{downloads_sas_token}"
    return blob_url_with_sas


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
