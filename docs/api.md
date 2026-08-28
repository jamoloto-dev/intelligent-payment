# API Reference & Endpoints

All APIs are exposed through the unified **API Gateway** on port `8000`.

Interactive Swagger documentation is available at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

---

## 1. Authentication & Users

### Register User
`POST /auth/register`
```json
{
  "email": "customer@example.com",
  "password": "SecurePassword123!",
  "first_name": "Jane",
  "last_name": "Doe",
  "role": "USER"
}
```
**Response (201 Created)**:
```json
{
  "id": "c1f76020-00e1-4c12-b131-01f65d648b29",
  "email": "customer@example.com",
  "first_name": "Jane",
  "last_name": "Doe",
  "role": "USER",
  "is_active": true,
  "created_at": "2026-08-28T22:00:00Z",
  "updated_at": "2026-08-28T22:00:00Z"
}
```

### Login
`POST /auth/login`
```json
{
  "email": "customer@example.com",
  "password": "SecurePassword123!"
}
```
**Response (200 OK)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": { ... }
}
```

### Current User Profile
`GET /auth/me` (Requires `Authorization: Bearer <token>`)

---

## 2. Products & Inventory

### Create Product (Admin Only)
`POST /products` (Requires `Authorization: Bearer <admin_token>`)
```json
{
  "name": "Wireless Noise Cancelling Headphones",
  "description": "Premium over-ear headphones",
  "price": 299.99,
  "currency": "USD",
  "stock_quantity": 50
}
```

### List Products
`GET /products?page=1&page_size=20&search=headphones`

### Get Product
`GET /products/{id}`

---

## 3. Orders

### Create Order
`POST /orders` (Requires `Authorization: Bearer <user_token>`)
```json
{
  "items": [
    {
      "product_id": "c1f76020-00e1-4c12-b131-01f65d648b29",
      "quantity": 2
    }
  ],
  "shipping_address": "123 Innovation Drive, Silicon Valley, CA",
  "currency": "USD"
}
```
**Response (201 Created)**:
```json
{
  "id": "e9b28a21-995b-439f-b98a-543cf63479a0",
  "user_id": "c1f76020-00e1-4c12-b131-01f65d648b29",
  "status": "PENDING",
  "total_amount": "599.98",
  "currency": "USD",
  "shipping_address": "123 Innovation Drive, Silicon Valley, CA",
  "items": [
    {
      "id": "...",
      "product_id": "c1f76020-00e1-4c12-b131-01f65d648b29",
      "product_name": "Wireless Noise Cancelling Headphones",
      "quantity": 2,
      "unit_price": "299.99",
      "subtotal": "599.98"
    }
  ],
  "created_at": "2026-08-28T22:05:00Z",
  "updated_at": "2026-08-28T22:05:00Z"
}
```

### Get Order
`GET /orders/{id}`

### Cancel Order
`POST /orders/{id}/cancel`

---

## 4. Payments

### Process Payment
`POST /payments` (Requires `Authorization: Bearer <user_token>`)
```json
{
  "order_id": "e9b28a21-995b-439f-b98a-543cf63479a0",
  "amount": 599.98,
  "currency": "USD",
  "payment_method_id": "pm_card_visa",
  "idempotency_key": "client_order_e9b28a21_attempt1",
  "billing_country": "US"
}
```
**Response (201 Created)**:
```json
{
  "id": "7b7d0391-4cf1-456b-a25e-0498a5948301",
  "order_id": "e9b28a21-995b-439f-b98a-543cf63479a0",
  "user_id": "c1f76020-00e1-4c12-b131-01f65d648b29",
  "amount": "599.98",
  "currency": "USD",
  "provider": "mock",
  "provider_transaction_id": "ch_mock_succ_8e29a1bf",
  "status": "SUCCEEDED",
  "idempotency_key": "client_order_e9b28a21_attempt1",
  "created_at": "2026-08-28T22:06:00Z",
  "updated_at": "2026-08-28T22:06:00Z"
}
```

### Refund Payment
`POST /payments/{id}/refund`
```json
{
  "amount": 599.98,
  "reason": "Customer cancellation request"
}
```

---

## 5. Fraud Detection

### Evaluate Transaction
`POST /fraud/check`
```json
{
  "transaction_id": "tx_check_1001",
  "order_id": "ord_1001",
  "user_id": "usr_1001",
  "amount": 6500.00,
  "currency": "USD",
  "recent_transactions_count_1h": 7,
  "recent_failed_payments_24h": 3,
  "billing_country": "US",
  "ip_country": "RU"
}
```
**Response (200 OK)**:
```json
{
  "transaction_id": "tx_check_1001",
  "order_id": "ord_1001",
  "user_id": "usr_1001",
  "risk_score": 100.0,
  "risk_level": "CRITICAL",
  "decision": "REJECT",
  "reasons": [
    "Transaction amount (6500.0 USD) exceeds critical threshold (5000.0)",
    "High transaction velocity: 7 attempts in the past hour (limit: 5)",
    "Multiple recent failed payments detected: 3 failures in last 24h",
    "Geolocation mismatch: Billing country 'US' != IP country 'RU'"
  ],
  "rules_triggered": [
    "CriticalAmountRule",
    "HighVelocityRule",
    "RepeatedFailuresRule",
    "GeolocationMismatchRule"
  ]
}
```

---

## 6. Health & Readiness Probes

Every microservice implements:
- `GET /health` -> Liveness check returning service status.
- `GET /ready` -> Readiness check verifying live database and broker connectivity.
