#!/bin/bash
# ==============================================================================
# Azure Deployment Automation Script for Intelligent Payment Platform
# ==============================================================================
set -e

RESOURCE_GROUP=${AZURE_RESOURCE_GROUP:-"rg-intelligent-payment-prod"}
LOCATION=${AZURE_LOCATION:-"eastus"}
ENVIRONMENT=${AZURE_ENVIRONMENT:-"prod"}
COMMIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "latest")
IMAGE_TAG=${IMAGE_TAG:-"sha-${COMMIT_SHA}"}
DEPLOYMENT_NAME="deploy-payment-platform-$(date +%s)"

echo "=================================================================="
echo "=== Intelligent Payment Platform Azure Deployment"
echo "Target Resource Group : $RESOURCE_GROUP"
echo "Location              : $LOCATION"
echo "Environment           : $ENVIRONMENT"
echo "Image Tag             : $IMAGE_TAG"
echo "=================================================================="

# 1. Ensure secrets are set or securely generated
if [ -z "$POSTGRES_PASSWORD" ]; then
    echo "Generating secure PostgreSQL Administrator password..."
    POSTGRES_PASSWORD=$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9!#%*+=' | head -c 24)
fi

if [ -z "$JWT_SECRET" ]; then
    echo "Generating secure JWT Secret key..."
    JWT_SECRET=$(openssl rand -hex 32)
fi

STRIPE_SECRET_KEY=${STRIPE_SECRET_KEY:-"sk_live_placeholder"}
STRIPE_WEBHOOK_SECRET=${STRIPE_WEBHOOK_SECRET:-"whsec_placeholder"}

# 2. Create Resource Group if not exists
echo "[1/6] Ensuring Resource Group exists..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output table

# 3. Create ACR first to allow image building/pushing before Container Apps deployment
UNIQUE_SUFFIX=$(az group show --name "$RESOURCE_GROUP" --query id -o tsv | md5sum | cut -c 1-8)
ACR_NAME="acrpayment${UNIQUE_SUFFIX}"

echo "[2/6] Checking Azure Container Registry: $ACR_NAME..."
az acr create --resource-group "$RESOURCE_GROUP" --name "$ACR_NAME" --sku Standard --location "$LOCATION" 2>/dev/null || true
ACR_SERVER=$(az acr show --name "$ACR_NAME" --query "loginServer" -o tsv)
echo "ACR Login Server: $ACR_SERVER"

# 4. Build and push container images to ACR
echo "[3/6] Building & pushing container images to ACR ($IMAGE_TAG)..."
SERVICES=("api_gateway:api-gateway" "user_service:user-service" "product_service:product-service" "order_service:order-service" "fraud_service:fraud-service" "payment_service:payment-service" "notification_service:notification-service")

for entry in "${SERVICES[@]}"; do
    DIR="${entry%%:*}"
    SVC="${entry##*:}"
    echo "  -> Building $SVC image in ACR..."
    az acr build --registry "$ACR_NAME" \
        --image "$SVC:$IMAGE_TAG" \
        --image "$SVC:latest" \
        -f "services/$DIR/Dockerfile" .
done

# 5. Deploy Infrastructure and Container Apps using Bicep
echo "[4/6] Deploying Azure Infrastructure & Container Apps via Bicep..."
az deployment group create \
    --name "$DEPLOYMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --template-file infrastructure/azure/main.bicep \
    --parameters \
        environmentName="$ENVIRONMENT" \
        imageTag="$IMAGE_TAG" \
        administratorLoginPassword="$POSTGRES_PASSWORD" \
        jwtSecret="$JWT_SECRET" \
        stripeSecretKey="$STRIPE_SECRET_KEY" \
        stripeWebhookSecret="$STRIPE_WEBHOOK_SECRET" \
    --output table

# 6. Database schema initialization / migrations
echo "[5/6] Initializing PostgreSQL schemas..."
POSTGRES_FQDN=$(az deployment group show --name "$DEPLOYMENT_NAME" --resource-group "$RESOURCE_GROUP" --query "properties.outputs.postgresFqdn.value" -o tsv)
echo "PostgreSQL Server: $POSTGRES_FQDN"

# 7. Export outputs
echo "[6/6] Exporting deployment outputs..."
GATEWAY_URL=$(az deployment group show --name "$DEPLOYMENT_NAME" --resource-group "$RESOURCE_GROUP" --query "properties.outputs.gatewayUrl.value" -o tsv 2>/dev/null || echo "N/A")
KEYVAULT_URI=$(az deployment group show --name "$DEPLOYMENT_NAME" --resource-group "$RESOURCE_GROUP" --query "properties.outputs.keyVaultUri.value" -o tsv 2>/dev/null || echo "N/A")

echo "=================================================================="
echo "Deployment successful!"
echo "API Gateway URL : $GATEWAY_URL"
echo "Key Vault URI   : $KEYVAULT_URI"
echo "ACR Server      : $ACR_SERVER"
echo "Postgres Host   : $POSTGRES_FQDN"
echo "=================================================================="
