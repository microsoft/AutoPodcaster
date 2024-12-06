# Image Indexer

The image indexer processes messages from the `image` queue and converts the image to text, which is then indexed.

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

## Run the Image indexer

```bash
python image_indexer.py
```
