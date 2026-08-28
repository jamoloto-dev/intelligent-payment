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
- Python 3.12+ (for local host scripting)

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

The platform provides complete Kubernetes manifests in `k8s/` (`infrastructure/kubernetes/`).

### Deployment Steps
1. Create the dedicated namespace:
   ```bash
   kubectl apply -f k8s/namespace.yaml
   ```
2. Apply ConfigMap and Secret manifests:
   ```bash
   kubectl apply -f k8s/configmap.yaml
   kubectl apply -f k8s/secret.yaml
   ```
3. Deploy persistent data stores:
   ```bash
   kubectl apply -f k8s/postgres.yaml
   kubectl apply -f k8s/redis.yaml
   kubectl apply -f k8s/mongodb.yaml
   ```
4. Deploy the application microservices:
   ```bash
   kubectl apply -f k8s/user-service.yaml
   kubectl apply -f k8s/product-service.yaml
   kubectl apply -f k8s/order-service.yaml
   kubectl apply -f k8s/fraud-service.yaml
   kubectl apply -f k8s/payment-service.yaml
   kubectl apply -f k8s/notification-service.yaml
   kubectl apply -f k8s/gateway.yaml
   ```
5. Apply Ingress routing:
   ```bash
   kubectl apply -f k8s/ingress.yaml
   ```
6. Verify pod readiness and liveness:
   ```bash
   kubectl get pods -n intelligent-payment
   kubectl get services -n intelligent-payment
   ```

---

## 3. Microsoft Azure Cloud Deployment

The platform is designed to run seamlessly on native Azure services:

### Architecture Decisions on Azure
1. **Azure Container Apps (ACA)**:
   - Serverless container orchestration based on Kubernetes (K8s) and KEDA.
   - Eliminates node management overhead while providing automatic HTTP and event-based scaling down to zero for low-traffic services.
2. **Azure Database for PostgreSQL (Flexible Server)**:
   - Managed relational database with automated backups, high availability, and SSL/TLS encryption by default.
3. **Azure Key Vault**:
   - Securely stores application secrets (JWT keys, database credentials, Stripe API keys).
   - Python microservices access secrets securely via Managed Identities with zero credentials in code.
4. **Azure Table Storage**:
   - High-speed, cost-effective NoSQL key-value store for tamper-evident compliance audit logs.
5. **Azure Functions (Python Serverless)**:
   - Executes asynchronous audit ingestion without provisioning continuous compute.

### Step-by-Step Azure Deployment
1. Log in to Azure CLI:
   ```bash
   az login
   az account set --subscription "<your-subscription-id>"
   ```
2. Run the deployment script:
   ```bash
   export AZURE_RESOURCE_GROUP="rg-intelligent-payment-prod"
   export AZURE_LOCATION="eastus"
   ./infrastructure/azure/deploy.sh
   ```
3. Push Docker images to Azure Container Registry (ACR):
   ```bash
   az acr login --name <acrLoginServer>
   docker tag intelligentpayment/api-gateway:1.0.0 <acrLoginServer>/api-gateway:1.0.0
   docker push <acrLoginServer>/api-gateway:1.0.0
   ```
