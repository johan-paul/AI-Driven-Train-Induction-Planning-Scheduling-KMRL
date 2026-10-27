# backend/auth.py
import os
from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader

# Name of the header clients must send
API_KEY_NAME = "x-api-key"

# fetch from env (fallback to a dev key—CHANGE this in prod)
API_KEY = os.getenv("KMRL_API_KEY", "dev_key_change_me")

# FastAPI helper that extracts header for OpenAPI docs + runtime
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def get_api_key(api_key_header: str = Security(api_key_header)):
    """
    Dependency to add to protected endpoints.
    Compares header value to env var API key and raises 401 if missing/invalid.
    """
    if api_key_header and api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API Key",
        headers={"WWW-Authenticate": "API Key"},
    )
