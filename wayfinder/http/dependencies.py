from fastapi import Header, HTTPException
import os

ADMIN_KEY = os.getenv("ADMIN_API_KEY")

def require_admin(x_api_key: str = Header(...)):
    if not ADMIN_KEY or x_api_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")