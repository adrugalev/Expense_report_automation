from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import Settings, get_settings
from .database import get_db
from .database_models import UserRecord
from .security import decode_access_token


def get_current_user(
    request: Request,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UserRecord:
    if settings.environment == "local-desktop" and settings.local_auth_bypass:
        local_email = (settings.local_auth_email or settings.admin_email).strip().lower()
        local_user = session.scalar(select(UserRecord).where(UserRecord.email == local_email))
        if not local_user or not local_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Локальная учётная запись не найдена или отключена",
            )
        return local_user

    token = request.cookies.get(settings.cookie_name)
    authorization = request.headers.get("Authorization", "")
    if not token and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    payload = decode_access_token(token, settings) if token else None
    user_id = str(payload.get("sub")) if payload and payload.get("sub") else None
    user = session.get(UserRecord, user_id) if user_id else None
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Требуется авторизация")
    return user


def require_roles(*roles: str) -> Callable:
    def dependency(user: UserRecord = Depends(get_current_user)) -> UserRecord:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
        return user

    return dependency
