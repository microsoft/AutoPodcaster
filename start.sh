source .env
# Check disableLocalAuth for Cosmos DB
disableLocalAuth=$(az cosmosdb show --ids $COSMOSDB_RESOURCE_ID --query "disableLocalAuth" -o tsv | tr -d '\n\r')

# Check allowSharedKeyAccess for Storage Account
allowSharedKeyAccess=$(az storage account show --ids $STORAGE_RESOURCE_ID --query "allowSharedKeyAccess" -o tsv | tr -d '\n\r')

# Check publicNetworkAccess for Cosmos DB
publicNetworkAccessCosmos=$(az cosmosdb show --ids $COSMOSDB_RESOURCE_ID --query "publicNetworkAccess" -o tsv | tr -d '\n\r')

# Check publicNetworkAccess for Storage Account
publicNetworkAccessStorage=$(az storage account show --ids $STORAGE_RESOURCE_ID --query "publicNetworkAccess" -o tsv | tr -d '\n\r')

echo "allowSharedKeyAccess: $allowSharedKeyAccess"
echo "publicNetworkAccessCosmos: $publicNetworkAccessCosmos"
echo "publicNetworkAccessStorage: $publicNetworkAccessStorage"

# Update disableLocalAuth if it's true
if [ "$disableLocalAuth" == "true" ]; then
  echo "Updating disableLocalAuth for Cosmos DB..."
  az resource update --ids $COSMOSDB_RESOURCE_ID --set properties.disableLocalAuth=false --latest-include-preview
  sleep 60
else
  echo "disableLocalAuth for Cosmos DB is already false."
fi

# Update allowSharedKeyAccess if it's false
if [ "$allowSharedKeyAccess" == "false" ]; then
  echo "Updating allowSharedKeyAccess for Storage Account..."
  az storage account update --ids $STORAGE_RESOURCE_ID --allow-shared-key-access true
else
  echo "allowSharedKeyAccess for Storage Account is already true."
fi

# Update publicNetworkAccess for Cosmos DB if it's disabled
if [ "$publicNetworkAccessCosmos" == "Disabled" ]; then
  echo "Enabling public network access for Cosmos DB..."
  az cosmosdb update --ids $COSMOSDB_RESOURCE_ID --public-network-access Enabled
else
  echo "Public network access for Cosmos DB is already enabled."
fi

# Update publicNetworkAccess for Storage Account if it's disabled
if [ "$publicNetworkAccessStorage" == "Disabled" ]; then
  echo "Enabling public network access for Storage Account..."
  az storage account update --ids $STORAGE_RESOURCE_ID --set publicNetworkAccess=Enabled
else
  echo "Public network access for Storage Account is already enabled."
fi

docker compose up