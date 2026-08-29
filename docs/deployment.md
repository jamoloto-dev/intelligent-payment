# Deployment Guide: Local, Kubernetes, and Azure

This guide explains how to deploy the **Intelligent Payment & Order Platform** across three target environments:
1. **Local Development (Docker Compose)**
2. **Kubernetes (Minikube / AKS / GKE)**
3. **Microsoft Azure Cloud (Container Apps / Key Vault / PostgreSQL Flexible Server)**

---

## 1. Local Development (Docker Compose)

### Prerequisites
- Docker Engine 24.0+
- Docker Compose v2.20+
- Python 3.12+ (for local host development)

### Steps
1. Clone the repository and copy the environment configuration:
   ```bash
   cp .env.example .env
   ```
2. Build and start all 10 containers (7 microservices + 3 datastores):
   ```bash
   docker compose up --build -d
   ```
3. Check container health status:
   ```bash
   docker compose ps
   ```
4. Verify the Gateway health and downstream connectivity:
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/ready
   ```
5. View logs across all services:
   ```bash
   docker compose logs -f
   ```
6. Teardown:
   ```bash
   docker compose down -v
   ```

---

## 2. Kubernetes Deployment

The platform provides complete, security-hardened Kubernetes manifests under `infrastructure/kubernetes/`.

### Prerequisites
- Kubernetes cluster 1.28+ (`minikube`, `kind`, `k3s`, or `AKS`)
- `kubectl` configured to your target cluster context

### Deployment Steps
1. Create the dedicated namespace:
   ```bash
   kubectl apply -f infrastructure/kubernetes/namespace.yaml
   ```
2. Apply ConfigMap and Secret manifests:
   ```bash
   kubectl apply -f infrastructure/kubernetes/configmap.yaml
   # For local/staging testing:
   kubectl apply -f infrastructure/kubernetes/secret.yaml
   # For production External Secrets Operator with Azure Key Vault:
   # kubectl apply -f infrastructure/kubernetes/external-secret.yaml
   ```
3. Apply Network Policies and Autoscaling rules:
   ```bash
   kubectl apply -f infrastructure/kubernetes/network-policy.yaml
   kubectl apply -f infrastructure/kubernetes/hpa.yaml
   ```
4. Deploy persistent data stores:
   ```bash
   kubectl apply -f infrastructure/kubernetes/postgres.yaml
   kubectl apply -f infrastructure/kubernetes/redis.yaml
   kubectl apply -f infrastructure/kubernetes/mongodb.yaml
   ```
5. Deploy the application microservices:
   ```bash
   kubectl apply -f infrastructure/kubernetes/user-service.yaml
   kubectl apply -f infrastructure/kubernetes/product-service.yaml
   kubectl apply -f infrastructure/kubernetes/order-service.yaml
   kubectl apply -f infrastructure/kubernetes/fraud-service.yaml
   kubectl apply -f infrastructure/kubernetes/payment-service.yaml
   kubectl apply -f infrastructure/kubernetes/notification-service.yaml
   kubectl apply -f infrastructure/kubernetes/gateway.yaml
   ```
6. Apply Ingress routing:
   ```bash
   kubectl apply -f infrastructure/kubernetes/ingress.yaml
   ```
7. Verify pod readiness and liveness:
   ```bash
   kubectl get pods -n intelligent-payment
   kubectl get services -n intelligent-payment
   ```

---

## 3. Microsoft Azure Cloud Deployment

The platform runs on native Azure services provisioned via Bicep Infrastructure as Code (`infrastructure/azure/main.bicep`):

### Architecture on Azure
1. **Azure Container Apps (ACA)**:
   - Serverless microservices running non-root container images with horizontal autoscaling.
   - User-Assigned Managed Identity (`id-payment-*`) used for passwordless secret resolution from Key Vault and image pulling from ACR.
2. **Azure Key Vault**:
   - Stores all application secrets (PostgreSQL administrator password, JWT secret keys, Stripe API keys).
   - Container Apps reference Key Vault secrets directly via `keyVaultUrl` and Managed Identity RBAC (`Key Vault Secrets User`).
3. **Azure Database for PostgreSQL (Flexible Server)**:
   - Managed PostgreSQL 16 server with dedicated databases per service (`user_service_db`, `product_service_db`, `order_service_db`, `payment_service_db`).
4. **Azure Storage Account**:
   - Table Storage for immutable audit logging and compliance event records.
5. **Azure Container Registry (ACR)**:
   - Private registry storing immutable images tagged with commit SHAs.

### Step-by-Step Azure Deployment
1. Log in to Azure CLI and select subscription:
   ```bash
   az login
   az account set --subscription "<your-subscription-id>"
   ```
2. Execute the automated deployment script:
   ```bash
   export AZURE_RESOURCE_GROUP="rg-intelligent-payment-prod"
   export AZURE_LOCATION="eastus"
   export AZURE_ENVIRONMENT="prod"
   ./infrastructure/azure/deploy.sh
   ```
3. The deployment script will:
   - Ensure the Resource Group exists.
   - Create Azure Container Registry.
   - Build and push container images for all 7 microservices tagged with the current commit SHA.
   - Deploy Bicep templates creating Key Vault, PostgreSQL Flexible Server, Container Apps Environment, and all Container Apps.
   - Initialize database schemas and export public Gateway URLs and Key Vault endpoints.
