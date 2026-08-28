# Security Policy

## Reporting Security Vulnerabilities

We take platform security with the utmost seriousness. If you believe you have discovered a vulnerability, security flaw, or exposed credential within the Intelligent Payment & Order Platform, please do **NOT** open a public GitHub issue.

Instead, please send an encrypted report to our security response team:
- **Email**: `security@intelligentpayment.local`
- **PGP Fingerprint**: `94E2 54A0 11C2 B6E3 8031  102C 49B8 07F1 D209 A177`

Please include:
1. Steps to reproduce the issue (proof-of-concept script or HTTP request trace).
2. Affected microservice(s) or endpoints.
3. Potential impact on confidentiality, integrity, or availability.

---

## Security Architecture & Best Practices

The platform enforces security by design across multiple layers:

### 1. Authentication & Session Management
- **Password Hashing**: Passwords are never stored in plaintext. They are salted and hashed using **bcrypt** with standard computational work factor.
- **JWT Cryptography**: JSON Web Tokens use HMAC-SHA256 (or asymmetric RS256 in enterprise mode). Tokens carry strict expiration (`exp`), issued-at (`iat`), and subject (`sub`) claims.
- **Role-Based Access Control (RBAC)**: Enforced via FastAPI dependency injection separating `USER` and `ADMIN` privileges.

### 2. Transport & Network Security
- **Strict HTTPS / TLS**: Ingress and cloud deployments enforce TLS 1.2+ minimum.
- **Reverse Proxy Gateway**: Direct database ports and internal services are isolated on private container networks, exposed externally exclusively through `api-gateway`.
- **CORS Configuration**: Restricts permitted cross-origin headers, methods, and credentials.

### 3. Data Protection & Sensitive Data Redaction
- **Log Sanitization**: The structured JSON logger automatically redacts sensitive fields (passwords, tokens, Stripe secret keys, and cardholder data) before emitting log records.
- **Zero Raw Card Storage**: Payment card data is processed directly through tokenized payment gateway APIs (Stripe). The platform never persists raw PANs (Primary Account Numbers) or CVVs, maintaining PCI-DSS Level 1 compliance posture.

### 4. Input Validation & SQL Injection Prevention
- **Pydantic Validation**: All inbound HTTP payloads and query parameters undergo strict Pydantic type, range, and format enforcement.
- **SQLAlchemy ORM Parameterization**: All database interactions use parameterized queries via SQLAlchemy async sessions, preventing SQL injection vulnerabilities.

### 5. Abuse Prevention & Resilience
- **Rate Limiting Middleware**: Protects API endpoints against brute force and DDoS attacks via sliding-window throttling (120 requests/minute per client IP).
- **Idempotency Safeguards**: Payment mutations support client-supplied idempotency keys preventing accidental duplicate charges.
- **Deterministic Fraud Scoring**: Analyzes transaction velocity, geographic consistency, account age, and failure frequency to block malicious or compromised actors.

### 6. Secrets Management & Cloud Security
- **No Hard-coded Secrets**: Secrets are loaded from OS environment variables or Azure Key Vault via Managed Identities.
- **Local Fallback**: Local development environment uses dummy `.env.example` placeholder keys with zero production exposure.
