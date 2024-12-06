#!/bin/bash

RESOURCE_GROUP_NAME=${RESOURCE_GROUP_NAME:-"rg-autopodcaster"}
LOCATION=${LOCATION:-"swedencentral"}
SERVICEBUS_NAMESPACE_NAME=${SERVICEBUS_NAMESPACE_NAME:-"sb-autopodcaster"}
COSMOSDB_ACCOUNT_NAME=${COSMOSDB_ACCOUNT_NAME:-"cosno-autopodcaster"}
AI_SEARCH_SERVICE_NAME=${AI_SEARCH_SERVICE_NAME:-"ais-autopodcaster"}
STORAGE_ACCOUNT_NAME=${STORAGE_ACCOUNT_NAME:-"stautopodcasterdutchdemo"}

az group create --name $RESOURCE_GROUP_NAME --location $LOCATION
az servicebus namespace create --resource-group $RESOURCE_GROUP_NAME --name $SERVICEBUS_NAMESPACE_NAME --location $LOCATION

# Create queues for text, PDF, video and website
az servicebus queue create --resource-group $RESOURCE_GROUP_NAME --namespace-name $SERVICEBUS_NAMESPACE_NAME --name "note" --enable-partitioning true
az servicebus queue create --resource-group $RESOURCE_GROUP_NAME --namespace-name $SERVICEBUS_NAMESPACE_NAME --name "pdf" --enable-partitioning true
az servicebus queue create --resource-group $RESOURCE_GROUP_NAME --namespace-name $SERVICEBUS_NAMESPACE_NAME --name "word" --enable-partitioning true
az servicebus queue create --resource-group $RESOURCE_GROUP_NAME --namespace-name $SERVICEBUS_NAMESPACE_NAME --name "video" --enable-partitioning true
az servicebus queue create --resource-group $RESOURCE_GROUP_NAME --namespace-name $SERVICEBUS_NAMESPACE_NAME --name "website" --enable-partitioning true
az servicebus queue create --resource-group $RESOURCE_GROUP_NAME --namespace-name $SERVICEBUS_NAMESPACE_NAME --name "visio" --enable-partitioning true
az servicebus queue create --resource-group $RESOURCE_GROUP_NAME --namespace-name $SERVICEBUS_NAMESPACE_NAME --name "image" --enable-partitioning true

# Create new queues for blog, podcast, and presentation
az servicebus queue create --resource-group $RESOURCE_GROUP_NAME --namespace-name $SERVICEBUS_NAMESPACE_NAME --name "blog" --enable-partitioning true
az servicebus queue create --resource-group $RESOURCE_GROUP_NAME --namespace-name $SERVICEBUS_NAMESPACE_NAME --name "podcast" --enable-partitioning true
az servicebus queue create --resource-group $RESOURCE_GROUP_NAME --namespace-name $SERVICEBUS_NAMESPACE_NAME --name "presentation" --enable-partitioning true

# Get the connection string for the Service Bus namespace
SERVICEBUS_CONNECTION_STRING=$(az servicebus namespace authorization-rule keys list --resource-group $RESOURCE_GROUP_NAME --namespace-name $SERVICEBUS_NAMESPACE_NAME --name RootManageSharedAccessKey --query primaryConnectionString --output tsv)

# Create a storage account for multipart file upload with a blob container
az storage account create --name $STORAGE_ACCOUNT_NAME --resource-group $RESOURCE_GROUP_NAME --location $LOCATION --sku Standard_LRS
az storage container create --name "uploads" --account-name $STORAGE_ACCOUNT_NAME --resource-group $RESOURCE_GROUP_NAME
az storage container create --name "downloads" --account-name $STORAGE_ACCOUNT_NAME --resource-group $RESOURCE_GROUP_NAME

# Get the connection string for the storage account
STORAGE_CONNECTION_STRING=$(az storage account show-connection-string --name $STORAGE_ACCOUNT_NAME --resource-group $RESOURCE_GROUP_NAME --query connectionString --output tsv)

#generate the SAS token for the downloads container
STORAGE_ACCOUNT_KEY1=$(az storage account keys list --resource-group $RESOURCE_GROUP_NAME --account-name $STORAGE_ACCOUNT_NAME --query '[0].value' --output tsv)
DOWNLOADS_SAS_TOKEN=$(az storage container generate-sas --name "downloads" --permissions r --expiry '2024-12-31T23:59Z' --https-only --account-name $STORAGE_ACCOUNT_NAME --account-key $STORAGE_ACCOUNT_KEY1 --output tsv)

# Generate the SAS URL for the downloads container
DOWNLOADS_SAS_URL="https://$STORAGE_ACCOUNT_NAME.blob.core.windows.net/downloads?$DOWNLOADS_SAS_TOKEN"

# Create a Cosmos DB account
az cosmosdb create --name $COSMOSDB_ACCOUNT_NAME --resource-group $RESOURCE_GROUP_NAME --locations regionName="Sweden Central" isZoneRedundant=false
# Create database
az cosmosdb sql database create --account-name $COSMOSDB_ACCOUNT_NAME --name "autopodcaster" --resource-group $RESOURCE_GROUP_NAME
# Create status container
az cosmosdb sql container create --name "status" --account-name $COSMOSDB_ACCOUNT_NAME --database-name "autopodcaster" --resource-group $RESOURCE_GROUP_NAME --partition-key-path "/id"
# Create inputs container
az cosmosdb sql container create --name "inputs" --account-name $COSMOSDB_ACCOUNT_NAME --database-name "autopodcaster" --resource-group $RESOURCE_GROUP_NAME --partition-key-path "/id"
# Create subjects container
az cosmosdb sql container create --name "subjects" --account-name $COSMOSDB_ACCOUNT_NAME --database-name "autopodcaster" --resource-group $RESOURCE_GROUP_NAME --partition-key-path "/id"
# Create outputs container
az cosmosdb sql container create --name "outputs" --account-name $COSMOSDB_ACCOUNT_NAME --database-name "autopodcaster" --resource-group $RESOURCE_GROUP_NAME --partition-key-path "/id"

# Get the connection string for the Cosmos DB account
COSMOSDB_CONNECTION_STRING=$(az cosmosdb list-connection-strings --name $COSMOSDB_ACCOUNT_NAME --resource-group $RESOURCE_GROUP_NAME --query connectionStrings[0].connectionString --output tsv)

# Create an Azure Search service
az search service create --name $AI_SEARCH_SERVICE_NAME --resource-group $RESOURCE_GROUP_NAME --location $LOCATION --sku standard

# Get the endpoint for the Azure Search service
AI_SEARCH_ENDPOINT=https://$AI_SEARCH_SERVICE_NAME.search.windows.net

# Get the admin key for the Azure Search service
AI_SEARCH_ADMIN_KEY=$(az search admin-key show --service-name $AI_SEARCH_SERVICE_NAME --resource-group $RESOURCE_GROUP_NAME --query primaryKey --output tsv)

# Add environment variables for Azure Speech
echo "AZURE_SPEECH_KEY=${AZURE_SPEECH_KEY}" >> .env
echo "AZURE_SPEECH_REGION=${AZURE_SPEECH_REGION}" >> .env

# Add environment variables for OpenAI
echo "AZURE_OPENAI_KEY=${AZURE_OPENAI_KEY}" >> .env
echo "AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}" >> .env
echo "AZURE_OPENAI_DEPLOYMENT=${AZURE_OPENAI_DEPLOYMENT}" >> .env
echo "AZURE_OPENAI_API_VERSION=${AZURE_OPENAI_API_VERSION}" >> .env
echo "AZURE_OPENAI_DEPLOYMENT_EMBEDDINGS=${AZURE_OPENAI_DEPLOYMENT_EMBEDDINGS}" >> .env

echo "Deployed resources"
echo "Service Bus Connection String"
echo "SERVICEBUS_CONNECTION_STRING=${SERVICEBUS_CONNECTION_STRING}" >> .env
echo "Storage Connection String"
echo "STORAGE_CONNECTION_STRING=${STORAGE_CONNECTION_STRING}" >> .env
echo "Downloads SAS Token"
echo "DOWNLOADS_SAS_TOKEN=${DOWNLOADS_SAS_TOKEN}" >> .env
echo "CosmosDb Connection String"
echo "COSMOSDB_CONNECTION_STRING=${COSMOSDB_CONNECTION_STRING}" >> .env
echo "AI Search Endpoint"
echo "AZURE_SEARCH_ENDPOINT=${AI_SEARCH_ENDPOINT}" >> .env
echo "AI Search Admin Key"
echo "AZURE_SEARCH_ADMIN_KEY=${AI_SEARCH_ADMIN_KEY}" >> .env