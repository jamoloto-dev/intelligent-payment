# Architectural Decision Records (ADRs)

## ADR-001: Microservices Architecture with Domain Isolation
* **Status**: Accepted
* **Context**: The platform manages distinct subdomains: user identity, product catalog/inventory, order management, payment gateway orchestration, fraud risk evaluation, and notifications.
* **Decision**: Adopt a microservices architecture with dedicated PostgreSQL databases per relational domain (`user_service_db`, `product_service_db`, `order_service_db`, `payment_service_db`).
* **Consequences**: Enhanced failure isolation and independent scalability. Requires event-driven asynchronous communication for cross-service state consistency.

---

## ADR-002: Dual Synchronous & Asynchronous Communication Strategy
* **Status**: Accepted
* **Context**: Inventory reservation and fraud risk scoring must be evaluated immediately before charging a card, whereas notifications and order status transitions can proceed asynchronously.
* **Decision**:
  - **Synchronous HTTP (FastAPI / httpx)**: Used for atomic stock reservation and pre-payment fraud assessment.
  - **Asynchronous Redis Pub/Sub**: Used for `OrderCreated`, `PaymentCompleted`, `PaymentFailed`, `PaymentRefunded`, and `FraudReviewRequired` events.
* **Consequences**: Fast client response times and non-blocking notification delivery without tight coupling.

---

## ADR-003: Deterministic Rule-Based Fraud Engine with Strategy Pattern
* **Status**: Accepted
* **Context**: Fraud detection requires immediate real-time decisions without introducing heavy machine learning pipeline dependencies during initial deployment, while remaining ready for future ML model integration.
* **Decision**: Implement a modular Strategy Pattern (`BaseFraudRule` interface) with rule evaluators for transaction velocity, high value thresholds, account age, and geolocation mismatches.
* **Consequences**: Transparent, auditable fraud decisions with clear explanatory reasons and plug-and-play ML model readiness.

---

## ADR-004: Payment Provider Abstraction Layer
* **Status**: Accepted
* **Context**: Continuous testing and offline local development cannot rely on active Stripe network credentials or live cards.
* **Decision**: Define `PaymentProviderInterface` and provide both `StripePaymentProvider` (real API) and `MockPaymentProvider` (deterministic sandbox simulation).
* **Consequences**: 100% automated test coverage and zero API key leaks in CI/CD environments.

---

## ADR-005: Serverless Azure Function for Audit Ingestion
* **Status**: Accepted
* **Context**: Compliance audit trails exhibit bursty, unpredictable event spikes. Running a 24/7 container service for audit logging introduces unnecessary idle compute costs.
* **Decision**: Use an Azure Function triggered by payment events to write tamper-evident audit entities to Azure Table Storage.
* **Consequences**: Zero idle cost, automatic per-event scaling, and complete compute decoupling.
