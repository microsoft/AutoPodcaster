targetScope = 'resourceGroup'

/* -------------------------------------------------------------------------- */
/*                                 PARAMETERS                                 */
/* -------------------------------------------------------------------------- */

@description('The location of all resources.')
param location string = resourceGroup().location

@description('The name of the workload.')
param workloadName string = 'autopod'

@description('The tag of the image to deploy.')
param imageTag string = '1.1.0'

@description('The environment name.')
@allowed([
  'dev'
  'test'
  'prod'
])
param environmentName string = 'dev'

/* ----------------------------- Infrastructure ----------------------------- */

@description('The name of the storage account. Defaults to "st<workloadName><environmentName><uniqueString(resourceGroup().id)>".')
param storageAccountName string = 'st${replace(workloadName, '-', '')}${environmentName}${take(uniqueString(resourceGroup().id), 5)}'

@description('The name of the storage account blob containers. Defaults to ["uploads", "downloads"].')
param storageAccountBlobContainersName string[] = ['uploads', 'downloads']

@description('The name of the Azure OpenAI resource. Defaults to "aoi-<workloadName>-<environmentName>".')
param azureOpenAIName string = 'aoi-${workloadName}-${environmentName}'

@description('The subdomain name of the Azure OpenAI resource. Default to "<workloadName><take(uniqueString(resourceGroup().id), 5)>".')
param azureOpenAISubDomainName string = '${replace(workloadName, '-', '')}${take(uniqueString(resourceGroup().id), 5)}'

@description('The name of the Log Analytics workspace. Default to "log-<workloadName>-<environmentName>".')
param logAnalyticsWorkspaceName string = 'log-${workloadName}-${environmentName}'

@description('The name of the container registry.')
param containerRegistryName string = 'cr${replace(workloadName, '-', '')}${environmentName}${take(uniqueString(resourceGroup().id), 5)}'

@description('The name of the user-managed identity for ACR pull. Default to "umi-acr-pull-<containerRegistryName>".')
param acrPullUserManagedIdentityName string = 'umi-acr-pull-${containerRegistryName}'

@description('The name of the container apps environment. Default to "cae-<workloadName>-<environmentName>".')
param containerAppsEnvironmentName string = 'cae-${workloadName}-${environmentName}'

@description('The name of the Cosmos DB account. Default to "cosno-<workloadName>-<environmentName>".')
param cosmosDbAccountName string = 'cosno-${workloadName}-${environmentName}'

@description('The name of the Cosmos DB database. Default to "autopodcaster".')
param cosmosDbDatabaseName string = 'autopodcaster'

@description('The name of the Cosmos DB SQL containers. Default to ["status", "inputs", "subjects", "outputs"].')
param cosmosDbSqlContainersName string[] = ['status', 'inputs', 'subjects', 'outputs']

@description('The name of the Service Bus namespace. Default to "sb-<workloadName>-<environmentName>-<take(uniqueString(resourceGroup().id), 5)>".')
param serviceBusNamespaceName string = 'sb-${workloadName}-${environmentName}-${take(uniqueString(resourceGroup().id), 5)}'

@description('The name of the Service Bus queues. Default to ["note", "pdf", "word", "video", "website", "visio", "image"].')
param serviceBusQueuesName string[] = ['note', 'pdf', 'word', 'video', 'website', 'visio', 'image']

@description('The name of the Search service. Default to "search-<workloadName>-<environmentName>".')
param searchServiceName string = 'search-${workloadName}-${environmentName}'

/* ----------------------------- Container Apps ----------------------------- */

@description('The tags for container apps. Default to empty.')
param tags object = {}

@description('The image name of the ui app')
param uiImageName string

@description('The image name of the indexer app')
param indexerImageName string

@description('The image name of the subject space app')
param subjectSpaceImageName string

@description('The image name of the output app')
param outputImageName string

@description('The image name of the note indexer app')
param noteIndexerImageName string

@description('The image name of the pdf indexer app')
param pdfIndexerImageName string

@description('The image name of the website indexer app')
param websiteIndexerImageName string

@description('The image name of the podcast generator app')
param podcastGeneratorImageName string

@description('The name of the ui container app. Default to "ca-ui-<environmentName>".')
param uiContainerAppName string = 'ca-ui-${environmentName}'

@description('The name of the indexer container app. Default to "ca-indexer-<environmentName>".')
param indexerContainerAppName string = 'ca-indexer-${environmentName}'

@description('The name of the subject space container app. Default to "ca-subject-space-<environmentName>".')
param subjectSpaceContainerAppName string = 'ca-subject-space-${environmentName}'

@description('The name of the output container app. Default to "ca-output-<environmentName>".')
param outputContainerAppName string = 'ca-output-${environmentName}'

@description('The name of the note indexer container app. Default to "ca-note-indexer-<environmentName>".')
param noteIndexerContainerAppName string = 'ca-note-indexer-${environmentName}'

@description('The name of the pdf indexer container app. Default to "ca-pdf-indexer-<environmentName>".')
param pdfIndexerContainerAppName string = 'ca-pdf-indexer-${environmentName}'

@description('The name of the website indexer container app. Default to "ca-website-indexer-<environmentName>".')
param websiteIndexerContainerAppName string = 'ca-website-indexer-${environmentName}'

@description('The name of the podcast generator container app. Default to "ca-podcast-generator-<environmentName>".')
param podcastGeneratorContainerAppName string = 'ca-podcast-generator-${environmentName}'

/* -------------------------------------------------------------------------- */
/*                                  VARIABLES                                 */
/* -------------------------------------------------------------------------- */

var acrPullRole = resourceId(
    'Microsoft.Authorization/roleDefinitions',
    '7f951dda-4ed3-4680-a7ca-43fe172d538d'
)
var keyVaultSecretUserRole = resourceId(
  'Microsoft.Authorization/roleDefinitions',
  '4633458b-17de-408a-b874-0445c86b69e6'
)
var storageBlobDelegatorRole = resourceId(
  'Microsoft.Authorization/roleDefinitions',
  'db58b8e5-c6ad-4a2a-8342-4190687cbf4a'
)
var storageBlobDataContributorRole = resourceId(
  'Microsoft.Authorization/roleDefinitions',
  'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
)
var cognitiveServicesOpenAIUserRole = resourceId(
  'Microsoft.Authorization/roleDefinitions',
  '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
)

/* -------------------------------------------------------------------------- */
/*                                  RESOURCES                                 */
/* -------------------------------------------------------------------------- */

/* ----------------------- Container Apps Environment ----------------------- */

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: containerAppsEnvironmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'azure-monitor'
    }
    zoneRedundant: false
    kedaConfiguration: {}
    daprConfiguration: {}
    customDomainConfiguration: {}
    workloadProfiles: [
      {
        workloadProfileType: 'Consumption'
        name: 'Consumption'
      }
    ]
    peerAuthentication: {
      mtls: {
        enabled: false
      }
    }
    peerTrafficConfiguration: {
      encryption: {
        enabled: false
      }
    }
  }
}

resource containerAppsEnvironmentDiagnosticSettings 'Microsoft.Insights/diagnosticsettings@2021-05-01-preview' = {
  name: 'diagnostic-settings'
  properties: {
    workspaceId: logAnalyticsWorkspace.id
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
      }
    ]
    logs: [
      {
        categoryGroup: 'allLogs'
        enabled: true
      }
    ]
  }
  scope: containerAppsEnvironment
}

/* --------------------------- Container Registry --------------------------- */

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: containerRegistryName
  location: location
  sku: {
    name: 'Standard'
  }
  properties: {
    adminUserEnabled: true
    policies: {
      quarantinePolicy: {
        status: 'disabled'
      }
      trustPolicy: {
        type: 'Notary'
        status: 'disabled'
      }
      retentionPolicy: {
        days: 7
        status: 'disabled'
      }
      exportPolicy: {
        status: 'enabled'
      }
      azureADAuthenticationAsArmPolicy: {
        status: 'enabled'
      }
      softDeletePolicy: {
        retentionDays: 7
        status: 'disabled'
      }
    }
    encryption: {
      status: 'disabled'
    }
    dataEndpointEnabled: false
    publicNetworkAccess: 'Enabled'
    networkRuleBypassOptions: 'AzureServices'
    zoneRedundancy: 'Disabled'
    anonymousPullEnabled: false
    metadataSearch: 'Disabled'
  }
}

resource acrPullUserManagedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-07-31-preview' = {
  name: acrPullUserManagedIdentityName
  location: location
}

resource containerRegistryAcrPullRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistry.id, acrPullUserManagedIdentity.id, acrPullRole)
  scope: containerRegistry
  properties: {
    principalId: acrPullUserManagedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: acrPullRole
  }
}


/* ------------------------------- Monitoring ------------------------------- */

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsWorkspaceName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
    features: {
      legacy: 0
      searchVersion: 1
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    workspaceCapping: {
      dailyQuotaGb: -1
    }
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

/* ------------------------------ Azure OpenAI ------------------------------ */

resource azureOpenAI 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' = {
  name: azureOpenAIName
  location: location
  sku: {
    name: 'S0'
  }
  kind: 'OpenAI'
  properties: {
    customSubDomainName: azureOpenAISubDomainName
    publicNetworkAccess: 'Enabled'
  }
}

resource gpt4oDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-04-01-preview' = {
  parent: azureOpenAI
  name: 'gpt-4o'
  sku: {
    name: 'GlobalStandard'
    capacity: 30
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: '2024-05-13'
    }
    versionUpgradeOption: 'OnceCurrentVersionExpired'
    currentCapacity: 450
    raiPolicyName: 'Microsoft.DefaultV2'
  }
}

// resource textEmbeddingsDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-04-01-preview' = {
//   parent: azureOpenAI
//   name: 'text-embedding-ada-002'
//   sku: {
//     name: 'P3'
//     capacity: 30
//   }
//   properties: {
//     model: {
//       format: 'OpenAI'
//       name: 'text-embedding-ada-002'
//     }
//     versionUpgradeOption: 'OnceCurrentVersionExpired'
//     currentCapacity: 450
//     raiPolicyName: 'Microsoft.DefaultV2'
//   }
// }

/* --------------------------------- Storage -------------------------------- */

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    publicNetworkAccess: 'Enabled'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: true
    largeFileSharesState: 'Enabled'
    supportsHttpsTrafficOnly: true
    accessTier: 'Hot'
  }
}

resource storageAccountBlobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
  properties: {}
}

resource storageAccountBlobContainers 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = [for containerName in storageAccountBlobContainersName: {
    parent: storageAccountBlobService
    name: containerName
  }
]

/* ------------------------------- Service Bus ------------------------------ */

resource serviceBusNamespace 'Microsoft.ServiceBus/namespaces@2024-01-01' = {
  name: serviceBusNamespaceName
  location: location
  sku: {
    name: 'Standard'
    tier: 'Standard'
  }
  properties: {
    disableLocalAuth: false
    publicNetworkAccess: 'Enabled'
  }
}

resource serviceBusQueues 'Microsoft.ServiceBus/namespaces/queues@2024-01-01' = [for queueName in serviceBusQueuesName: {
    parent: serviceBusNamespace
    name: queueName
  }
]

var serviceBusEndpoint = '${serviceBusNamespaceName}/AuthorizationRules/RootManageSharedAccessKey'
var serviceBusPrimaryConnectionString = 'Endpoint=sb://${serviceBusNamespace.name}.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=${listKeys(serviceBusEndpoint, serviceBusNamespace.apiVersion).primaryKey}'

/* -------------------------------- Cosmos DB ------------------------------- */

resource cosmosDbAccount 'Microsoft.DocumentDB/databaseAccounts@2021-04-15' = {
  name: cosmosDbAccountName
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    locations: [
      {
        locationName: location
        failoverPriority: 0
      }
    ]
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    enableMultipleWriteLocations: false
    enableAutomaticFailover: true
    isVirtualNetworkFilterEnabled: false
    enableFreeTier: false
    publicNetworkAccess: 'Enabled'
    disableKeyBasedMetadataWriteAccess: false
  }
}

resource cosmosDbDatabase 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-12-01-preview' = {
  parent: cosmosDbAccount
  name: cosmosDbDatabaseName
  properties: {
    resource: {
        id: cosmosDbDatabaseName
    }
  }
}

resource cosmosDbContainers 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-12-01-preview' = [for containerName in cosmosDbSqlContainersName: {
    parent: cosmosDbDatabase
    name: containerName
    properties: {
      resource: {
        id: containerName
      }
    }
  }
]

/* ----------------------------- Container Apps ----------------------------- */

// resource AssignRoleCognitiveServicesOpenAIUserToAiImageProcessing 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
//   name: guid(azureOpenAI.id, gpt4oDeployment.name, workloadName, aiImageProcessingServiceContainerApp.name, cognitiveServicesOpenAIUserRole)
//   scope: azureOpenAI
//   properties: {
//     principalId: aiImageProcessingServiceContainerApp.identity.principalId
//     principalType: 'ServicePrincipal'
//     roleDefinitionId: cognitiveServicesOpenAIUserRole
//   }
// }

resource indexerContainerApp 'Microsoft.App/containerapps@2024-02-02-preview' = {
  name: indexerContainerAppName
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${acrPullUserManagedIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    workloadProfileName: 'Consumption'
    configuration: {
      secrets: []
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8081
        exposedPort: 0
        transport: 'Auto'
        allowInsecure: false
        corsPolicy: {
          allowedOrigins: [
            '*'
          ]
          allowedHeaders: [
            '*'
          ]
          maxAge: 0
          allowCredentials: false
        }
      }
      registries: [
        {
          server: containerRegistry.properties.loginServer
          identity: acrPullUserManagedIdentity.id
        }
      ]
      maxInactiveRevisions: 100
    }
    template: {
      containers: [
        {
          image: !empty(indexerImageName) ? indexerImageName : '${containerRegistry.properties.loginServer}/indexer:${imageTag}'
          name: 'indexer'
          env: [
            {
              name: 'SERVICEBUS_CONNECTION_STRING'
              value: serviceBusPrimaryConnectionString
            }
            {
              name: 'STORAGE_CONNECTION_STRING'
              value: ''
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          probes: []
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 10
      }
      volumes: []
    }
  }
}

resource subjectSpaceContainerApp 'Microsoft.App/containerapps@2024-02-02-preview' = {
  name: subjectSpaceContainerAppName
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${acrPullUserManagedIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    workloadProfileName: 'Consumption'
    configuration: {
      secrets: []
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8082
        exposedPort: 0
        transport: 'Auto'
        allowInsecure: false
        corsPolicy: {
          allowedOrigins: [
            '*'
          ]
          allowedHeaders: [
            '*'
          ]
          maxAge: 0
          allowCredentials: false
        }
      }
      registries: [
        {
          server: containerRegistry.properties.loginServer
          identity: acrPullUserManagedIdentity.id
        }
      ]
      maxInactiveRevisions: 100
    }
    template: {
      containers: [
        {
          image: !empty(subjectSpaceImageName) ? subjectSpaceImageName : '${containerRegistry.properties.loginServer}/subject-space:${imageTag}'
          name: 'subject-space'
          env: [
            {
              name: 'SERVICEBUS_CONNECTION_STRING'
              value: ''
            }
            {
              name: 'COSMOSDB_CONNECTION_STRING'
              value: ''
            }
            {
              name: 'AZURE_SEARCH_ENDPOINT'
              value: '' 
            }
            {
              name: 'AZURE_SEARCH_ADMIN_KEY'
              value: '' 
            }
            {
              name: 'AZURE_OPENAI_KEY'
              value: '' 
            }
            {
              name: 'AZURE_OPENAI_ENDPOINT'
              value: '' 
            }
            {
              name: 'AZURE_OPENAI_API_VERSION'
              value: '' 
            }
            {
              name: 'AZURE_OPENAI_DEPLOYMENT_EMBEDDINGS'
              value: '' 
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          probes: []
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 10
      }
      volumes: []
    }
  }
}

resource outputContainerApp 'Microsoft.App/containerapps@2024-02-02-preview' = {
  name: outputContainerAppName
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${acrPullUserManagedIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    workloadProfileName: 'Consumption'
    configuration: {
      secrets: []
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8083
        exposedPort: 0
        transport: 'Auto'
        allowInsecure: false
        corsPolicy: {
          allowedOrigins: [
            '*'
          ]
          allowedHeaders: [
            '*'
          ]
          maxAge: 0
          allowCredentials: false
        }
      }
      registries: [
        {
          server: containerRegistry.properties.loginServer
          identity: acrPullUserManagedIdentity.id
        }
      ]
      maxInactiveRevisions: 100
    }
    template: {
      containers: [
        {
          image: !empty(outputImageName) ? outputImageName : '${containerRegistry.properties.loginServer}/output:${imageTag}'
          name: 'output'
          env: [
            {
              name: 'SUBJECT_SPACE_ENDPOINT'
              value: 'https://${subjectSpaceContainerApp.properties.configuration.ingress.fqdn}'
            }
            {
              name: 'SERVICEBUS_CONNECTION_STRING'
              value: serviceBusPrimaryConnectionString
            }
            {
              name: 'COSMOSDB_CONNECTION_STRING'
              value: ''
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          probes: []
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 10
      }
      volumes: []
    }
  }
}

resource uiContainerApp 'Microsoft.App/containerApps@2024-02-02-preview' = {
  name: uiContainerAppName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned, UserAssigned'
    userAssignedIdentities: {
      '${acrPullUserManagedIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    workloadProfileName: 'Consumption'
    configuration: {
      secrets: []
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 5173 
        transport: 'tcp'
        allowInsecure: false
      }
      registries: [
        {
          server: containerRegistry.properties.loginServer
          identity: acrPullUserManagedIdentity.id
        }
      ]
    }
    template: {
      containers: [
        {
          image: !empty(uiImageName) ? uiImageName: '${containerRegistry.properties.loginServer}/ui:${imageTag}'
          name: 'ui'
          env: [
            {
              name: 'STATUS_ENDPOINT'
              value: azureOpenAI.properties.endpoint
            }
            {
              name: 'SUBJECT_SPACE_ENDPOINT'
              value: azureOpenAI.properties.endpoint
            }
            {
              name: 'OUTPUT_ENDPOINT'
              value: azureOpenAI.properties.endpoint
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          probes: []
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 10
      }
      volumes: []
    }
  }
}
