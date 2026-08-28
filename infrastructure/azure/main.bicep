// Azure Infrastructure as Code (Bicep) for Intelligent Payment Platform
targetScope = 'resourceGroup'

@description('Primary location for all resources')
param location string = resourceGroup().location

@description('Environment name (e.g. staging, prod)')
param environmentName string = 'prod'

@description('Unique suffix for globally unique resources')
param uniqueSuffix string = uniqueString(resourceGroup().id)

// 1. Azure Container Registry
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

// 2. Azure Key Vault
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv-payment-${uniqueSuffix}'
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

// 3. Azure Storage Account (for Table Storage audit logs)
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'stpayment${uniqueSuffix}'
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

// 4. Azure Database for PostgreSQL Flexible Server
resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-03-01-preview' = {
  name: 'psql-payment-${uniqueSuffix}'
  location: location
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    version: '16'
    administratorLogin: 'psqladmin'
    administratorLoginPassword: 'ChangeMeInProduction!123'
    storage: {
      storageSizeGB: 32
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
  }
}

// 5. Azure Container Apps Environment
resource containerAppEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: 'cae-payment-${environmentName}'
  location: location
  properties: {
    zoneRedundant: false
  }
}

output acrLoginServer string = containerRegistry.properties.loginServer
output keyVaultUri string = keyVault.properties.vaultUri
output storageAccountName string = storageAccount.name
output postgresFqdn string = postgresServer.properties.fullyQualifiedDomainName
