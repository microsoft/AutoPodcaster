# Subject_space

The Subject_space is an API to manage subject spaces. A subject space is a curated collection of documents related to a specific subject, i.e. a collection of document ids.

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
. ../infra/deploy.sh
```

## Create the environment variables file

```bash
echo SERVICEBUS_CONNECTION_STRING=${SERVICEBUS_CONNECTION_STRING} > .env
echo COSMOSDB_CONNECTION_STRING=${COSMOSDB_CONNECTION_STRING} >> .env
echo AZURE_SEARCH_ENDPOINT=${AI_SEARCH_ENDPOINT} >> .env
echo AZURE_SEARCH_ADMIN_KEY=${AI_SEARCH_ADMIN_KEY} >> .env
```
Also put the 
OPENAI_API_KEY=
OPENAI_AZURE_ENDPOINT=
OPENAI_AZURE_DEPLOYMENT=
OPENAI_API_VERSION=
OPENAI_AZURE_DEPLOYMENT_EMBEDDINGS=
AZURE_SPEECH_KEY=
AZURE_SPEECH_REGION=


## Run the indexer

```bash
fastapi dev subject_space.py --port 8082
```

## API Endpoints

The following endpoints are defined in `subject_space.py`:

### GET /subject
Retrieve a list of all subjects.

```json
[
    {
        "id": "1",
        "name": "Mathematics",
        "description": "Study of numbers, quantities, and shapes.",
        "created_at": "2023-01-01T12:00:00Z"
    },
    {
        "id": "2",
        "name": "Physics",
        "description": "Study of matter, energy, and the interactions between them.",
        "created_at": "2023-01-02T12:00:00Z"
    }
]
```

### POST /subject
Create a new subject.

#### Input
```json
{
    "subject": "string""
}
```

#### Output
```json
{
    "id": "string",
    "name": "string",
    "description": "string",
    "created_at": "string"
}
```

### GET /subjects/{subject_id}
Retrieve details of a specific subject by ID.

#### Output
```json
{
    "id": "1",
    "name": "Mathematics",
    "description": "Study of numbers, quantities, and shapes.",
    "created_at": "2023-01-01T12:00:00Z"
}
```

### PUT /subjects/{subject_id}
Update an existing subject by ID.

#### Input
```json
{
    "name": "string",
    "description": "string"
}
```

#### Output
```json
{
    "id": "string",
    "name": "string",
    "description": "string",
    "created_at": "string"
}
```

### DELETE /subjects/{subject_id}
Delete a specific subject by ID.