# Website Indexer

The website indexer processes messages from the `website` queue and indexes website URLs.

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

## Run the website indexer

```bash
python note_indexer.py
```
