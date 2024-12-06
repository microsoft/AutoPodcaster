# PDF Indexer

The PDF indexer processes messages from the `pdf` queue and indexes PDF files.

## Install requirements

```bash
pip install -r requirements.txt
```

## Deploy the infrastructure

If not already done, deploy the infrastructure:

```bash
. ../infra/deploy.sh
```

## Create the environment variables file

```bash
echo SERVICEBUS_CONNECTION_STRING=${SERVICEBUS_CONNECTION_STRING} > .env
echo COSMOSDB_CONNECTION_STRING=${COSMOSDB_CONNECTION_STRING} >> .env
echo STATUS_ENDPOINT=${STATUS_ENDPOINT} >> .env
```

## Run the PDF indexer

```bash
python pdf_indexer.py
```
