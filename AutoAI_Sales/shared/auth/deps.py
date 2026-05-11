from __future__ import annotations

from fastapi import Header, HTTPException, status

from shared.config.settings import get_settings


settings = get_settings()


def get_dealership_id(x_dealership_id: str | None = Header(default=None, alias="X-Dealership-ID")) -> str:
    dealership_id = (x_dealership_id or settings.default_dealership_id).strip()
    if not dealership_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing dealership identifier")
    return dealership_id


def require_site_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    if not settings.require_site_api_key:
        return
    if not settings.site_api_key or x_api_key != settings.site_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


def require_admin_token(authorization: str | None = Header(default=None, alias="Authorization")) -> None:
    if authorization != f"Bearer {settings.internal_admin_token}":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
