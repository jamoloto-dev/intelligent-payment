# Platform Architecture Documentation

## 1. System Overview

The **Intelligent Payment & Order Platform** is a distributed, event-driven microservices architecture built with **Python 3.12**, **FastAPI**, **PostgreSQL**, **Redis**, and **MongoDB / Azure Table Storage**.

It provides high-throughput order management, inventory locking, third-party payment processing (Stripe / Mock Provider), fraud risk scoring, and asynchronous event notifications.

---

## 2. Microservices Architecture Diagram

```mermaid
flowchart TD
    Client(["🌐 Client / Front-end"]) -->|HTTP/REST| Gateway["🚪 API Gateway (Port 8000)"]

    subgraph Core_Services ["Microservices Tier"]
        Gateway -->|/auth, /users| UserSvc["👤 User Service (Port 8001)"]
        Gateway -->|/products| ProdSvc["📦 Product Service (Port 8002)"]
        Gateway -->|/orders| OrderSvc["🛒 Order Service (Port 8003)"]
        Gateway -->|/payments| PaySvc["💳 Payment Service (Port 8005)"]
        Gateway -->|/fraud| FraudSvc["🛡️ Fraud Service (Port 8004)"]
        Gateway -->|/notifications| NotifSvc["🔔 Notification Service (Port 8006)"]
    end

    subgraph Data_Tier ["Databases & State"]
        UserSvc -->|Async SQLAlchemy| UserDB[("🐘 PostgreSQL: user_service_db")]
        ProdSvc -->|Row Locking / ACID| ProdDB[("🐘 PostgreSQL: product_service_db")]
        OrderSvc -->|Relational Schema| OrderDB[("🐘 PostgreSQL: order_service_db")]
        PaySvc -->|Transactions| PayDB[("🐘 PostgreSQL: payment_service_db")]
        FraudSvc -->|Risk Records| MongoFraud[("🍃 MongoDB / Azure Tables")]
        NotifSvc -->|Audit Logs| MongoNotif[("🍃 MongoDB / Azure Tables")]
    end

    subgraph Event_Bus ["Asynchronous Event Broker (Redis)"]
        OrderSvc -.->|OrderCreated| RedisBus[("⚡ Redis Pub/Sub & Streams")]
        PaySvc -.->|PaymentCompleted / PaymentFailed| RedisBus
        FraudSvc -.->|FraudReviewRequired| RedisBus
        RedisBus -.->|Event Consumption| OrderSvc
        RedisBus -.->|Event Consumption| NotifSvc
    end

    subgraph Payment_Gateway ["External Gateway Integration"]
        PaySvc -->|Charges & Refunds| StripeAPI["💳 Stripe Sandbox / Mock Provider"]
    end

    subgraph Serverless_Tier ["Cloud Serverless Functions"]
        RedisBus -.->|Payment Events| AzureFunc["⚡ Azure Function (Audit Ingestion)"]
        AzureFunc -->|Immutable Log| AzureTables[("📊 Azure Table Storage")]
    end
```

---

## 3. Microservice Responsibilities

| Service Name | Port | Database | Primary Responsibility |
|---|---|---|---|
| **`api-gateway`** | 8000 | In-Memory / Cache | Reverse proxy routing, rate limiting (120 req/min), CORS, request tracing (`X-Request-ID`), aggregated OpenAPI Swagger. |
| **`user-service`** | 8001 | PostgreSQL (`user_service_db`) | User registration, bcrypt password hashing, JWT token issuance & claims, RBAC. |
| **`product-service`** | 8002 | PostgreSQL (`product_service_db`) | Product catalog, pricing, atomic stock reservation & release with `SELECT FOR UPDATE` pessimistic locking. |
| **`order-service`** | 8003 | PostgreSQL (`order_service_db`) | Order lifecycle management, inventory reservation orchestration, event publishing. |
| **`payment-service`** | 8005 | PostgreSQL (`payment_service_db`) | Stripe integration, mock sandbox provider, idempotency keys, refund lifecycle, webhook verification. |
| **`fraud-service`** | 8004 | MongoDB / Azure Tables | Deterministic rule-based scoring engine (velocity, amounts, age, failure counts) with extensible strategy pattern for ML models. |
| **`notification-service`** | 8006 | MongoDB / Azure Tables | Asynchronous Redis event consumer, multi-channel notification dispatcher (log, email, webhooks). |
| **`audit-function`** | Serverless | Azure Table Storage | Serverless event handler generating tamper-evident compliance audit records. |

---

## 4. Synchronous vs Asynchronous Communication

```mermaid
sequenceDiagram
    autonumber
    actor Customer as Customer
    participant Gateway as API Gateway
    participant OrderSvc as Order Service
    participant ProdSvc as Product Service
    participant PaySvc as Payment Service
    participant FraudSvc as Fraud Service
    participant Stripe as Stripe Gateway
    participant Redis as Redis Event Bus
    participant NotifSvc as Notification Service

    Customer->>Gateway: POST /orders (items, address)
    Gateway->>OrderSvc: Forward POST /orders
    OrderSvc->>ProdSvc: POST /products/{id}/reserve (Atomic Lock)
    ProdSvc-->>OrderSvc: 200 OK (Stock Reserved)
    OrderSvc->>OrderSvc: Create PENDING Order in DB
    OrderSvc-->>Gateway: 201 Created (Order data)
    Gateway-->>Customer: 201 Created (Order data)

    Customer->>Gateway: POST /payments (order_id, amount, idempotency_key)
    Gateway->>PaySvc: Forward POST /payments
    PaySvc->>FraudSvc: POST /fraud/check (amount, velocity, geo)
    FraudSvc-->>PaySvc: 200 OK (Decision: APPROVE, Score: 5)
    PaySvc->>Stripe: Create Charge / PaymentIntent
    Stripe-->>PaySvc: 200 OK (Charge Succeeded)
    PaySvc->>PaySvc: Save Payment status=SUCCEEDED
    PaySvc->>Redis: Publish PaymentCompleted Event
    PaySvc-->>Gateway: 201 Created (Payment response)
    Gateway-->>Customer: 201 Created (Payment response)

    par Asynchronous Event Handling
        Redis->>OrderSvc: Consume PaymentCompleted
        OrderSvc->>OrderSvc: Update Order status to PAID
    and
        Redis->>NotifSvc: Consume PaymentCompleted
        NotifSvc->>NotifSvc: Dispatch Customer Email & Save Notification Log
    end
```
