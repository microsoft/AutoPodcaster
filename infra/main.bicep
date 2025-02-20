targetScope = 'subscription'

@minLength(2)
@maxLength(32)
@description('Name of the the azd environment.')
param environmentName string = 'ai-workshop'

@minLength(2)
@description('Primary location for all resources.')
param location string

@description('Name of the the resource group. Default: rg-{environmentName}')
param resourceGroupName string = ''

@description('The deployment env name.')
@allowed([
  'dev'
  'test'
  'prod'
])
param deployEnv string = 'dev'

param utcValue string = utcNow()
var tags = {
  'azd-env-name': environmentName
  'utc-time': utcValue
}

var banner = 'mcr.microsoft.com/azurespringapps/default-banner:distroless-2024022107-66ea1a62-87936983'

@description('Organize resources in a resource group')
resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: !empty(resourceGroupName) ? resourceGroupName : 'rg-${environmentName}'
  location: location
  tags: tags
}

module deploy 'deploy.bicep' = {
  name: 'deploy-${environmentName}'
  scope: rg
  params: {
    workloadName: environmentName
    environmentName: deployEnv
    uiImageName: banner
    indexerImageName: banner
    subjectSpaceImageName: banner
    outputImageName: banner
    noteIndexerImageName: banner
    pdfIndexerImageName: banner
    websiteIndexerImageName: banner
    podcastGeneratorImageName: banner
    tags: {
      'azd-env-name': environmentName
      'java-acc-samples-java-ai': 'true'
    }
  }
}

output resourceGroupName string = rg.name
// output acrLoginServer string = deploy.outputs.acrLoginServer
// output azdProvisionTimestamp string = 'azd-${environmentName}-${utcValue}'
// output apiGatewayContainerAppName string = deploy.outputs.apiGatewayContainerAppName
// output blobStorageServiceContainerAppName string = deploy.outputs.blobStorageServiceContainerAppName
// output imageProcessingServiceContainerAppName string = deploy.outputs.imageProcessingServiceContainerAppName
// output itemCategoryServiceContainerAppName string = deploy.outputs.itemCategoryServiceContainerAppName
// output aiShopUiContainerApps string = deploy.outputs.aiShopUiContainerApps
