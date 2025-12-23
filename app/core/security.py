# app/core/security.py
from __future__ import annotations
from dotenv import load_dotenv
load_dotenv()



import os
import time
from typing import Any, Dict, Optional, Set

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

try:
    import jwt  # PyJWT
except ImportError as e:
    raise RuntimeError(
        "Missing dependency: PyJWT. Install with: pip install PyJWT"
    ) from e


# ---------- Config (env-driven) ----------

API_KEY_HEADER_NAME = os.getenv("API_KEY_HEADER_NAME", "X-API-Key")

JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ISSUER = os.getenv("JWT_ISSUER", "reimbursement_api")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "reimbursement_clients")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Comma-separated API keys in env (recommended for dev).
# In production, prefer a DB/secret manager.
VALID_API_KEYS_RAW = os.getenv("VALID_API_KEYS", "")
VALID_API_KEYS: Set[str] = {k.strip() for k in VALID_API_KEYS_RAW.split(",") if k.strip()}


def _require_jwt_secret():
    if not JWT_SECRET or len(JWT_SECRET) < 16:
        raise RuntimeError(
            "JWT_SECRET is not set or too short. Set a strong secret (>=16 chars) in environment."
        )


# ---------- API Key auth (token issuance) ----------

api_key_header = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False)


def validate_api_key(api_key: Optional[str]) -> str:
    """
    Validates incoming API key against allow-list.
    Returns the api_key if valid; raises HTTP 401 otherwise.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Missing API key header '{API_KEY_HEADER_NAME}'.",
        )
    if api_key not in VALID_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )
    return api_key


def api_key_auth(api_key: Optional[str] = Depends(api_key_header)) -> str:
    """
    FastAPI dependency: validates API key and returns it.
    Use this only on the token endpoint.
    """
    return validate_api_key(api_key)


# ---------- JWT creation & validation ----------

def create_access_token(
    subject: str,
    expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Creates a signed JWT access token.
    subject: typically a client id or identifier (we use the API key hash/label in this simple version).
    """
    _require_jwt_secret()

    now = int(time.time())
    exp = now + int(expires_minutes) * 60

    payload: Dict[str, Any] = {
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": now,
        "nbf": now,
        "exp": exp,
        "sub": subject,
        "typ": "access",
    }
    if extra_claims:
        payload.update(extra_claims)

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    # PyJWT may return bytes in older versions; normalize to str.
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


bearer_scheme = HTTPBearer(auto_error=False)


def decode_and_verify_token(token: str) -> Dict[str, Any]:
    """
    Decodes JWT and validates signature + standard claims.
    Raises HTTP 401 on failure.
    """
    _require_jwt_secret()
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
            options={"require": ["exp", "iat", "sub", "iss", "aud"]},
        )
        if payload.get("typ") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type.",
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired.",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
        )


def jwt_auth(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Dict[str, Any]:
    """
    FastAPI dependency for protected endpoints.
    Requires: Authorization: Bearer <token>
    Returns decoded token payload.
    """
    if not creds or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )
    return decode_and_verify_token(creds.credentials)
