# Output API

The Output API is an API to generate an output for a subject space. It contains the API to manage the output generation and trigger output generator agents by sending messages to the service bus.

## Install requirements

```bash
pip install -r requirements.txt
```

Install fast api standard library

```bash
pip install fastapi[standard]==0.112.0
```

## Deploy the infrastructure

```bash
. ../../infra/deploy.sh
```

## Create the environment variables file

```bash
echo SERVICEBUS_CONNECTION_STRING=${SERVICEBUS_CONNECTION_STRING} > .env
echo SUBJECT_SPACE_API_URL=${SUBJECT_SPACE_API_URL} >> .env
```

## Run the output API

```bash
fastapi dev output.py --port 8083
```

# Output Service Bus
Queue: blog, podcast, presentation
```json
{
  "request_id": "0b310ec5-e055-4d36-b2d6-9bf7db1ee83f",
  "subject_id": "d8b1b3b0-4b7b-4b7b-8b7b-8b7b8b7b8b7b",
  "subject_json": {
    "uuid": "d8b1b3b0-4b7b-4b7b-8b7b-8b7b8b7b8b7b",
    "subject": "LoRa fine-tuning",
    "date": "2021-02-06",
    "last_update": "2021-02-06",
    "inputs": ["d8b1b3b0-4b7b-4b7b-8b7b-8b7b8b7b8b7b"],
    "vectorDbName": "vectorDbName"
  },
  "output_type": "blog"
}
```
