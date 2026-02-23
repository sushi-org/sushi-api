from __future__ import annotations

from fastapi import Header, HTTPException, status

from app.config import Config


def verify_admin_key(authorization: str = Header(...)) -> None:
    expected = f"Bearer {Config.ADMIN_API_KEY}"
    if not Config.ADMIN_API_KEY or authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin API key",
        )
