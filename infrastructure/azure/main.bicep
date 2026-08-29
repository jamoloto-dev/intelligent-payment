// Azure Infrastructure as Code (Bicep) for Intelligent Payment Platform
targetScope = 'resourceGroup'

@description('Primary location for all resources')
param location string = resourceGroup().location

@description('Environment name (e.g. staging, prod)')
param environmentName string = 'prod'

@description('Unique suffix for globally unique resources')
param uniqueSuffix string = uniqueString(resourceGroup().id)

@description('Image tag or commit SHA for container deployments')
param imageTag string = 'latest'

@description('PostgreSQL Administrator username')
param postgresAdminLogin string = 'psqladmin'

@description('PostgreSQL Administrator secure password')
@secure()
param administratorLoginPassword string

@description('JWT Secret Key for Token Verification')
@secure()
param jwtSecret string

@description('Stripe API Secret Key')
@secure()
param stripeSecretKey string = ''

@description('Stripe Webhook Signing Secret')
@secure()
param stripeWebhookSecret string = ''

// 1. User Assigned Managed Identity
resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-payment-${environmentName}-${uniqueSuffix}'
  location: location
}

// 2. Azure Container Registry
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: 'acrpayment${uniqueSuffix}'
  location: location
  sku: {
    name: 'Standard'
  }
  properties: {
    adminUserEnabled: false
  }
}

// ACR Pull Role Assignment for Managed Identity
// AcrPull role definition ID: 7f951dda-4ed3-4680-a7ca-43fe172d538d
resource acrPullRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistry.id, managedIdentity.id, '7f951dda-4ed3-4680-a7ca-43fe172d538d')
  scope: containerRegistry
  properties: {
    principalId: managedIdentity.properties.principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalType: 'ServicePrincipal'
  }
}

// 3. Azure Key Vault
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv-pay-${take(uniqueSuffix, 16)}'
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
  }
}

// Key Vault Secrets User Role Assignment for Managed Identity
// Key Vault Secrets User role definition ID: 4633458b-17de-408a-b874-0445c86b69e6
resource kvSecretsUserRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, managedIdentity.id, '4633458b-17de-408a-b874-0445c86b69e6')
  scope: keyVault
  properties: {
    principalId: managedIdentity.properties.principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
    principalType: 'ServicePrincipal'
  }
}

// Key Vault Secrets (Secured via RBAC)
resource secretPostgresPassword 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'postgres-password'
  properties: {
    value: administratorLoginPassword
  }
}

resource secretJwt 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'jwt-secret'
  properties: {
    value: jwtSecret
  }
}

resource secretStripeKey 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'stripe-secret-key'
  properties: {
    value: stripeSecretKey
  }
}

resource secretStripeWebhook 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'stripe-webhook-secret'
  properties: {
    value: stripeWebhookSecret
  }
}

// 4. Azure Storage Account (for Table Storage audit logs)
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'stpay${take(uniqueSuffix, 18)}'
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
  }
}

// Storage Table Data Contributor role definition ID: 0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3
resource storageTableRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, managedIdentity.id, '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3')
  scope: storageAccount
  properties: {
    principalId: managedIdentity.properties.principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3')
    principalType: 'ServicePrincipal'
  }
}

// 5. Azure Database for PostgreSQL Flexible Server
resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-03-01-preview' = {
  name: 'psql-payment-${uniqueSuffix}'
  location: location
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    version: '16'
    administratorLogin: postgresAdminLogin
    administratorLoginPassword: administratorLoginPassword
    storage: {
      storageSizeGB: 32
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
  }
}

// PostgreSQL Firewall Rule to allow internal Azure services
resource postgresAllowAzureServices 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-03-01-preview' = {
  parent: postgresServer
  name: 'AllowAllAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// PostgreSQL Microservice Databases
resource dbUser 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-03-01-preview' = {
  parent: postgresServer
  name: 'user_service_db'
}

resource dbProduct 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-03-01-preview' = {
  parent: postgresServer
  name: 'product_service_db'
}

resource dbOrder 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-03-01-preview' = {
  parent: postgresServer
  name: 'order_service_db'
}

resource dbPayment 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-03-01-preview' = {
  parent: postgresServer
  name: 'payment_service_db'
}

// 6. Log Analytics Workspace (for Container Apps monitoring)
resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: 'log-payment-${environmentName}'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// 7. Azure Container Apps Environment
resource containerAppEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: 'cae-payment-${environmentName}'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsWorkspace.properties.customerId
        sharedKey: logAnalyticsWorkspace.listKeys().primarySharedKey
      }
    }
    zoneRedundant: false
  }
}

// Common Container App Settings
var acrHost = containerRegistry.properties.loginServer
var postgresHost = postgresServer.properties.fullyQualifiedDomainName

// 8. Redis Container App
resource caRedis 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'ca-redis'
  location: location
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      ingress: {
        external: false
        targetPort: 6379
        transport: 'tcp'
      }
    }
    template: {
      containers: [
        {
          name: 'redis'
          image: 'redis:7-alpine'
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
    }
  }
}

// 9. Microservices Container Apps

// User Service
resource caUserService 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'ca-user-service'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      registries: [
        {
          server: acrHost
          identity: managedIdentity.id
        }
      ]
      secrets: [
        {
          name: 'postgres-password'
          keyVaultUrl: secretPostgresPassword.properties.secretUri
          identity: managedIdentity.id
        }
        {
          name: 'jwt-secret'
          keyVaultUrl: secretJwt.properties.secretUri
          identity: managedIdentity.id
        }
      ]
      ingress: {
        external: false
        targetPort: 8001
        transport: 'auto'
      }
    }
    template: {
      containers: [
        {
          name: 'user-service'
          image: '${acrHost}/user-service:${imageTag}'
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            { name: 'SERVICE_NAME', value: 'user-service' }
            { name: 'POSTGRES_HOST', value: postgresHost }
            { name: 'POSTGRES_PORT', value: '5432' }
            { name: 'POSTGRES_USER', value: postgresAdminLogin }
            { name: 'POSTGRES_DB', value: 'user_service_db' }
            { name: 'POSTGRES_PASSWORD', secretRef: 'postgres-password' }
            { name: 'DATABASE_URL', value: 'postgresql+asyncpg://${postgresAdminLogin}:secretRef:postgres-password@${postgresHost}:5432/user_service_db' }
            { name: 'JWT_SECRET', secretRef: 'jwt-secret' }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: { path: '/health', port: 8001 }
              initialDelaySeconds: 10
              periodSeconds: 10
            }
            {
              type: 'Readiness'
              httpGet: { path: '/health', port: 8001 }
              initialDelaySeconds: 5
              periodSeconds: 5
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 5
      }
    }
  }
}

// Product Service
resource caProductService 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'ca-product-service'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      registries: [
        {
          server: acrHost
          identity: managedIdentity.id
        }
      ]
      secrets: [
        {
          name: 'postgres-password'
          keyVaultUrl: secretPostgresPassword.properties.secretUri
          identity: managedIdentity.id
        }
        {
          name: 'jwt-secret'
          keyVaultUrl: secretJwt.properties.secretUri
          identity: managedIdentity.id
        }
      ]
      ingress: {
        external: false
        targetPort: 8002
        transport: 'auto'
      }
    }
    template: {
      containers: [
        {
          name: 'product-service'
          image: '${acrHost}/product-service:${imageTag}'
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            { name: 'SERVICE_NAME', value: 'product-service' }
            { name: 'POSTGRES_HOST', value: postgresHost }
            { name: 'POSTGRES_PORT', value: '5432' }
            { name: 'POSTGRES_USER', value: postgresAdminLogin }
            { name: 'POSTGRES_DB', value: 'product_service_db' }
            { name: 'POSTGRES_PASSWORD', secretRef: 'postgres-password' }
            { name: 'DATABASE_URL', value: 'postgresql+asyncpg://${postgresAdminLogin}:secretRef:postgres-password@${postgresHost}:5432/product_service_db' }
            { name: 'JWT_SECRET', secretRef: 'jwt-secret' }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: { path: '/health', port: 8002 }
              initialDelaySeconds: 10
              periodSeconds: 10
            }
            {
              type: 'Readiness'
              httpGet: { path: '/health', port: 8002 }
              initialDelaySeconds: 5
              periodSeconds: 5
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 5
      }
    }
  }
}

// Fraud Service
resource caFraudService 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'ca-fraud-service'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      registries: [
        {
          server: acrHost
          identity: managedIdentity.id
        }
      ]
      secrets: [
        {
          name: 'jwt-secret'
          keyVaultUrl: secretJwt.properties.secretUri
          identity: managedIdentity.id
        }
      ]
      ingress: {
        external: false
        targetPort: 8004
        transport: 'auto'
      }
    }
    template: {
      containers: [
        {
          name: 'fraud-service'
          image: '${acrHost}/fraud-service:${imageTag}'
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            { name: 'SERVICE_NAME', value: 'fraud-service' }
            { name: 'JWT_SECRET', secretRef: 'jwt-secret' }
            { name: 'REDIS_URL', value: 'redis://ca-redis:6379/0' }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: { path: '/health', port: 8004 }
              initialDelaySeconds: 10
              periodSeconds: 10
            }
            {
              type: 'Readiness'
              httpGet: { path: '/health', port: 8004 }
              initialDelaySeconds: 5
              periodSeconds: 5
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 5
      }
    }
  }
}

// Order Service
resource caOrderService 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'ca-order-service'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      registries: [
        {
          server: acrHost
          identity: managedIdentity.id
        }
      ]
      secrets: [
        {
          name: 'postgres-password'
          keyVaultUrl: secretPostgresPassword.properties.secretUri
          identity: managedIdentity.id
        }
        {
          name: 'jwt-secret'
          keyVaultUrl: secretJwt.properties.secretUri
          identity: managedIdentity.id
        }
      ]
      ingress: {
        external: false
        targetPort: 8003
        transport: 'auto'
      }
    }
    template: {
      containers: [
        {
          name: 'order-service'
          image: '${acrHost}/order-service:${imageTag}'
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            { name: 'SERVICE_NAME', value: 'order-service' }
            { name: 'POSTGRES_HOST', value: postgresHost }
            { name: 'POSTGRES_PORT', value: '5432' }
            { name: 'POSTGRES_USER', value: postgresAdminLogin }
            { name: 'POSTGRES_DB', value: 'order_service_db' }
            { name: 'POSTGRES_PASSWORD', secretRef: 'postgres-password' }
            { name: 'DATABASE_URL', value: 'postgresql+asyncpg://${postgresAdminLogin}:secretRef:postgres-password@${postgresHost}:5432/order_service_db' }
            { name: 'REDIS_URL', value: 'redis://ca-redis:6379/0' }
            { name: 'PRODUCT_SERVICE_URL', value: 'http://ca-product-service:8002' }
            { name: 'JWT_SECRET', secretRef: 'jwt-secret' }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: { path: '/health', port: 8003 }
              initialDelaySeconds: 10
              periodSeconds: 10
            }
            {
              type: 'Readiness'
              httpGet: { path: '/health', port: 8003 }
              initialDelaySeconds: 5
              periodSeconds: 5
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 5
      }
    }
  }
}

// Payment Service
resource caPaymentService 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'ca-payment-service'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      registries: [
        {
          server: acrHost
          identity: managedIdentity.id
        }
      ]
      secrets: [
        {
          name: 'postgres-password'
          keyVaultUrl: secretPostgresPassword.properties.secretUri
          identity: managedIdentity.id
        }
        {
          name: 'jwt-secret'
          keyVaultUrl: secretJwt.properties.secretUri
          identity: managedIdentity.id
        }
        {
          name: 'stripe-secret-key'
          keyVaultUrl: secretStripeKey.properties.secretUri
          identity: managedIdentity.id
        }
        {
          name: 'stripe-webhook-secret'
          keyVaultUrl: secretStripeWebhook.properties.secretUri
          identity: managedIdentity.id
        }
      ]
      ingress: {
        external: false
        targetPort: 8005
        transport: 'auto'
      }
    }
    template: {
      containers: [
        {
          name: 'payment-service'
          image: '${acrHost}/payment-service:${imageTag}'
          resources: {
            cpu: json('0.5')
            memory: '1.0Gi'
          }
          env: [
            { name: 'SERVICE_NAME', value: 'payment-service' }
            { name: 'POSTGRES_HOST', value: postgresHost }
            { name: 'POSTGRES_PORT', value: '5432' }
            { name: 'POSTGRES_USER', value: postgresAdminLogin }
            { name: 'POSTGRES_DB', value: 'payment_service_db' }
            { name: 'POSTGRES_PASSWORD', secretRef: 'postgres-password' }
            { name: 'DATABASE_URL', value: 'postgresql+asyncpg://${postgresAdminLogin}:secretRef:postgres-password@${postgresHost}:5432/payment_service_db' }
            { name: 'REDIS_URL', value: 'redis://ca-redis:6379/0' }
            { name: 'FRAUD_SERVICE_URL', value: 'http://ca-fraud-service:8004' }
            { name: 'ORDER_SERVICE_URL', value: 'http://ca-order-service:8003' }
            { name: 'STRIPE_SECRET_KEY', secretRef: 'stripe-secret-key' }
            { name: 'STRIPE_WEBHOOK_SECRET', secretRef: 'stripe-webhook-secret' }
            { name: 'USE_MOCK_PAYMENT_PROVIDER', value: 'false' }
            { name: 'JWT_SECRET', secretRef: 'jwt-secret' }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: { path: '/health', port: 8005 }
              initialDelaySeconds: 10
              periodSeconds: 10
            }
            {
              type: 'Readiness'
              httpGet: { path: '/health', port: 8005 }
              initialDelaySeconds: 5
              periodSeconds: 5
            }
          ]
        }
      ]
      scale: {
        minReplicas: 2
        maxReplicas: 10
      }
    }
  }
}

// Notification Service
resource caNotificationService 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'ca-notification-service'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      registries: [
        {
          server: acrHost
          identity: managedIdentity.id
        }
      ]
      secrets: [
        {
          name: 'jwt-secret'
          keyVaultUrl: secretJwt.properties.secretUri
          identity: managedIdentity.id
        }
      ]
      ingress: {
        external: false
        targetPort: 8006
        transport: 'auto'
      }
    }
    template: {
      containers: [
        {
          name: 'notification-service'
          image: '${acrHost}/notification-service:${imageTag}'
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            { name: 'SERVICE_NAME', value: 'notification-service' }
            { name: 'REDIS_URL', value: 'redis://ca-redis:6379/0' }
            { name: 'JWT_SECRET', secretRef: 'jwt-secret' }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: { path: '/health', port: 8006 }
              initialDelaySeconds: 10
              periodSeconds: 10
            }
            {
              type: 'Readiness'
              httpGet: { path: '/health', port: 8006 }
              initialDelaySeconds: 5
              periodSeconds: 5
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 5
      }
    }
  }
}

// API Gateway (Public Facing)
resource caApiGateway 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'ca-api-gateway'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      registries: [
        {
          server: acrHost
          identity: managedIdentity.id
        }
      ]
      secrets: [
        {
          name: 'jwt-secret'
          keyVaultUrl: secretJwt.properties.secretUri
          identity: managedIdentity.id
        }
      ]
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
      }
    }
    template: {
      containers: [
        {
          name: 'api-gateway'
          image: '${acrHost}/api-gateway:${imageTag}'
          resources: {
            cpu: json('0.5')
            memory: '1.0Gi'
          }
          env: [
            { name: 'SERVICE_NAME', value: 'api-gateway' }
            { name: 'USER_SERVICE_URL', value: 'http://ca-user-service:8001' }
            { name: 'PRODUCT_SERVICE_URL', value: 'http://ca-product-service:8002' }
            { name: 'ORDER_SERVICE_URL', value: 'http://ca-order-service:8003' }
            { name: 'FRAUD_SERVICE_URL', value: 'http://ca-fraud-service:8004' }
            { name: 'PAYMENT_SERVICE_URL', value: 'http://ca-payment-service:8005' }
            { name: 'NOTIFICATION_SERVICE_URL', value: 'http://ca-notification-service:8006' }
            { name: 'REDIS_URL', value: 'redis://ca-redis:6379/0' }
            { name: 'JWT_SECRET', secretRef: 'jwt-secret' }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: { path: '/health', port: 8000 }
              initialDelaySeconds: 10
              periodSeconds: 10
            }
            {
              type: 'Readiness'
              httpGet: { path: '/ready', port: 8000 }
              initialDelaySeconds: 5
              periodSeconds: 5
            }
          ]
        }
      ]
      scale: {
        minReplicas: 2
        maxReplicas: 10
      }
    }
  }
}

// Outputs
output acrLoginServer string = containerRegistry.properties.loginServer
output keyVaultUri string = keyVault.properties.vaultUri
output storageAccountName string = storageAccount.name
output postgresFqdn string = postgresServer.properties.fullyQualifiedDomainName
output managedIdentityClientId string = managedIdentity.properties.clientId
output gatewayFqdn string = caApiGateway.properties.configuration.ingress.fqdn
output gatewayUrl string = 'https://${caApiGateway.properties.configuration.ingress.fqdn}'
