#!/bin/bash
# ==============================================================================
# Azure Deployment Automation Script for Intelligent Payment Platform
# ==============================================================================
set -e

RESOURCE_GROUP=${AZURE_RESOURCE_GROUP:-"rg-intelligent-payment-prod"}
LOCATION=${AZURE_LOCATION:-"eastus"}
DEPLOYMENT_NAME="deploy-payment-platform-$(date +%s)"

echo "=== Intelligent Payment Platform Azure Deployment ==="
echo "Target Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"

# 1. Create Resource Group if not exists
echo "[1/4] Ensuring Resource Group exists..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output table

# 2. Deploy Infrastructure using Bicep
echo "[2/4] Deploying Azure Infrastructure via Bicep template..."
az deployment group create \
    --name "$DEPLOYMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --template-file infrastructure/azure/main.bicep \
    --parameters environmentName="prod" \
    --output table

echo "[3/4] Exporting deployment outputs..."
ACR_SERVER=$(az deployment group show --name "$DEPLOYMENT_NAME" --resource-group "$RESOURCE_GROUP" --query "properties.outputs.acrLoginServer.value" -o tsv)
KEYVAULT_URI=$(az deployment group show --name "$DEPLOYMENT_NAME" --resource-group "$RESOURCE_GROUP" --query "properties.outputs.keyVaultUri.value" -o tsv)

echo "ACR Server: $ACR_SERVER"
echo "Key Vault URI: $KEYVAULT_URI"

echo "[4/4] Azure deployment completed successfully!"
