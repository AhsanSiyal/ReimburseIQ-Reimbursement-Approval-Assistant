# Reimbursement Approval Assistant (FastAPI + RAG + OpenAI) — with API Key + JWT Security

This project provides a **Reimbursement Approval Assistant** designed to be integrated with an ERP system.

It:
- ingests a company reimbursement **rulebook** (policy documents),
- retrieves relevant policy sections via **RAG** (vector search),
- runs a **deterministic rules engine** (thresholds/caps/receipts/deadlines),
- uses **OpenAI LLM** to generate a manager-friendly decision + suggestions,
- returns a structured JSON response with policy **citations**,
- exposes everything via **FastAPI** endpoints,
- protects endpoints using **API Key authentication + JWT access tokens**.

---

## Architecture Overview

### Runtime flow (ERP → API)
1. ERP (or Postman) calls `/v1/auth/token` using an **API key** in header `X-API-Key`.
2. API returns a short-lived **JWT access token**.
3. ERP calls `/v1/claims/evaluate` with `Authorization: Bearer <JWT>`.
4. Server:
   - runs deterministic checks,
   - runs RAG retrieval against the ingested rulebook,
   - calls OpenAI LLM to create a manager-friendly decision with citations,
   - validates and returns structured response.

### Offline/Admin flow (Policy ingestion)
1. Put policy files in `data/policies/*.md`
2. Run ingestion script to build vector index.

---

## Expense Categories Supported

The Reimbursement Approval Assistant currently handles and validates the following **expense categories**.
These categories are enforced at the **API schema level**, checked in the **deterministic rule engine**, and
used by the **RAG + LLM layer** to retrieve and cite the correct policy rules.

### Supported Categories
- **MEALS** – Business meals during travel or offsite work
- **LODGING** – Hotels and accommodation during business travel
- **AIRFARE** – Flights for business travel
- **RAIL** – Train travel for business purposes
- **TAXI** – Taxi and ride-hailing services
- **PUBLIC_TRANSIT** – Metro, bus, tram, and other public transport
- **MILEAGE** – Personal vehicle usage reimbursed per kilometer
- **CLIENT_ENTERTAINMENT** – Client meals or entertainment (requires attendees + receipt)
- **OFFICE** – Office and home-office related expenses
- **TRAINING** – Courses, conferences, and certifications
- **OTHER** – Catch-all category for uncommon business expenses

### Notes
- Any category outside this list is automatically rejected (HTTP 422).
- Each category has category-specific validation rules.
- Categories are embedded into the RAG queries to ensure correct policy citations.

---

## Project Structure

```
reimbursement-rag/
  app/
    main.py
    core/
      config.py
      security.py
    rag/
      ingest.py
      retriever.py
      splitter.py
      prompts.py
    rules/
      rule_engine.py
    schemas/
      claim.py
      response.py
  data/
    policies/
      rulebook.md
    reimbursement_form_schema.json
    index/
      faiss.index
      meta.json
  scripts/
    ingest_policies.py
  requirements.txt
  .env.example
  README.md
```

---

## Security Model (API Key → JWT)

### Step 1: API Key Authentication
Endpoint:
- `POST /v1/auth/token`

Client sends:
- Header `X-API-Key: <api_key>`

If valid, server returns a JWT access token.

### Step 2: JWT Authentication
Endpoint:
- `POST /v1/claims/evaluate`

Client sends:
- Header `Authorization: Bearer <JWT>`

The server verifies signature, expiration, issuer, audience, and token type.

---

## Setup (Conda, Python 3.11)

```bash
conda create -n reimbursement311 python=3.11 -y
conda activate reimbursement311
conda install -c conda-forge numpy=1.26 faiss-cpu -y
pip install -r requirements.txt
```

---

## Environment Variables

Create `.env` from `.env.example`.

Minimum required:

```ini
OPENAI_API_KEY=sk-...
JWT_SECRET=change_this_to_a_long_random_secret_32_chars_min
VALID_API_KEYS=dev-key-1,streamlit-key-2025,prod-key-abc
```

---

## Policy Ingestion

```bash
python -m scripts.ingest_policies
```

This generates:
- `data/index/faiss.index`
- `data/index/meta.json`

---

## Run the API

```bash
uvicorn app.main:app --reload --port 8000
```

---

## Postman Testing

### 1. Health Check
```
GET http://localhost:8000/health
```

### 2. Get Token
```
POST http://localhost:8000/v1/auth/token
Header: X-API-Key: dev-key-1
```

### 3. Evaluate Claim
```
POST http://localhost:8000/v1/claims/evaluate
Headers:
  Authorization: Bearer <token>
  Content-Type: application/json
```

---

## ERP Integration Pattern

- ERP stores API key securely.
- ERP exchanges API key for JWT.
- ERP calls evaluate endpoint per reimbursement.
- Response is stored for audit (decision + citations).

---

## Production Notes

- Rotate API keys and JWT secrets.
- Store audit logs.
- Add rate limiting and monitoring.
- Replace env-based key storage with a secure vault.
