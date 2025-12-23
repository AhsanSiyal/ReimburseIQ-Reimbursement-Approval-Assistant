# app/main.py

from fastapi import FastAPI, HTTPException, Depends
from dotenv import load_dotenv
from typing import List
import json
from openai import OpenAI

from app.core.config import settings
from app.core.security import api_key_auth, create_access_token, jwt_auth
from app.schemas.claim import Claim
from app.schemas.response import EvaluateResponse
from app.rules.rule_engine import evaluate_claim
from app.rag.retriever import PolicyRetriever
from app.rag.prompts import SYSTEM_POLICY_ANALYST, build_user_prompt

load_dotenv()

app = FastAPI(title="Reimbursement Approval Assistant (RAG)", version="1.0.0")

retriever: PolicyRetriever | None = None
client: OpenAI | None = None


@app.on_event("startup")
def startup():
    """
    Initializes OpenAI client and RAG retriever at startup.
    """
    global retriever, client

    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set. Set it in environment or .env")

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    try:
        retriever = PolicyRetriever()
    except Exception as e:
        # Allow server to start, but evaluation will fail with clear message.
        retriever = None
        print(f"[WARN] Retriever not ready (did you run ingestion?): {e}")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/v1/auth/token")
def issue_token(api_key: str = Depends(api_key_auth)):
    """
    Exchange API Key (X-API-Key) for a short-lived JWT access token.

    Request:
      Header: X-API-Key: <your_api_key>

    Response:
      { "access_token": "...", "token_type": "bearer", "expires_in": 1800 }
    """
    # For a simple setup, we use the API key itself as the subject.
    # In production, prefer a client_id and avoid putting raw keys into 'sub'.
    token = create_access_token(subject=api_key)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 30 * 60,
    }


@app.post("/v1/claims/evaluate", response_model=EvaluateResponse)
def evaluate_endpoint(
    claim: Claim,
    _auth=Depends(jwt_auth),  # <-- Protect endpoint with JWT
):
    """
    Evaluates a reimbursement claim using:
    1) Deterministic rules engine (caps, receipts, deadlines, etc.)
    2) RAG retrieval over policy documents (FAISS)
    3) OpenAI LLM reasoning to produce manager-friendly summary + citations
       (Uses chat.completions for compatibility, since `client.responses` is not available
        in the user's OpenAI SDK build.)
    """
    if retriever is None:
        raise HTTPException(
            status_code=500,
            detail="Policy index not found or retriever not initialized. Run: python -m scripts.ingest_policies",
        )
    if client is None:
        raise HTTPException(status_code=500, detail="OpenAI client not initialized")

    claim_dict = claim.model_dump()

    # 1) Deterministic checks
    deterministic = evaluate_claim(claim_dict)

    # 2) Build RAG queries
    queries: List[str] = [
        "General reimbursement eligibility, receipts, documentation, approvals"
    ]
    for ln in claim_dict["lines"]:
        queries.append(
            f"Rules for category={ln['category']}, amount={ln['amount']} {ln['currency']}, "
            f"vendor={ln['vendor']}, desc={ln['description']}"
        )

    # 3) Retrieve top policy excerpts and de-duplicate
    merged = []
    seen = set()
    for q in queries[:8]:
        for hit in retriever.search(q, top_k=settings.RAG_TOP_K):
            key = (hit["source_path"], hit["section_title"], hit["text"][:120])
            if key not in seen:
                seen.add(key)
                merged.append(hit)

    # Limit context size
    policy_excerpts = merged[:10]

    # 4) Build prompt
    user_prompt = build_user_prompt(claim_dict, deterministic, policy_excerpts)

    # 5) OpenAI call (Chat Completions) - compatible with your SDK build
    completion = client.chat.completions.create(
        model=settings.OPENAI_CHAT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_POLICY_ANALYST},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
    )

    out_text = completion.choices[0].message.content
    if not out_text:
        raise HTTPException(status_code=500, detail="OpenAI returned empty content")

    # 6) Parse and validate JSON
    try:
        parsed = json.loads(out_text)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"LLM did not return valid JSON. Error: {e}. Raw output: {out_text[:1000]}",
        )

    # 7) Enrich citations using retrieved excerpts (best-effort)
    rule_to_meta = {}
    for ex in policy_excerpts:
        for rid in ex.get("rule_ids") or []:
            rule_to_meta.setdefault(
                rid,
                {
                    "section_title": ex.get("section_title"),
                    "source_path": ex.get("source_path"),
                },
            )

    for c in parsed.get("citations", []) or []:
        rid = c.get("rule_id")
        meta = rule_to_meta.get(rid)
        if meta:
            c.setdefault("section_title", meta.get("section_title"))
            c.setdefault("source_path", meta.get("source_path"))

    # 8) Compose ERP-safe response via Pydantic model
    try:
        api_response = EvaluateResponse(
            decision=parsed["decision"],
            summary=parsed["summary"],
            approval_route=deterministic["approval_route"],
            claim_total=deterministic["claim_total"],
            lines=parsed["lines"],
            missing_info=parsed.get("missing_info", []),
            citations=parsed.get("citations", []),
            debug={
                "deterministic": deterministic,
                "rag_excerpts_used": len(policy_excerpts),
            },
        )
        return api_response
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to validate response against EvaluateResponse schema: {e}",
        )
