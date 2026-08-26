from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..database import get_db
from ..database_models import UserRecord
from ..dependencies import get_current_user
from ..schemas.auth import LoginRequest, SessionResponse, UserResponse
from ..security import create_access_token, verify_password


router = APIRouter(prefix="/auth", tags=["auth"])


def _user_response(user: UserRecord) -> UserResponse:
    return UserResponse(id=user.id, email=user.email, full_name=user.full_name, role=user.role)


@router.post("/login", response_model=SessionResponse)
def login(
    data: LoginRequest,
    response: Response,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SessionResponse:
    user = session.scalar(select(UserRecord).where(UserRecord.email == data.email.lower()))
    if not user or not user.is_active or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль")
    token = create_access_token(user.id, user.role, settings)
    response.set_cookie(
        settings.cookie_name,
        token,
        max_age=settings.access_token_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return SessionResponse(user=_user_response(user), expires_in=settings.access_token_minutes * 60)


@router.get("/me", response_model=UserResponse)
def me(user: UserRecord = Depends(get_current_user)) -> UserResponse:
    return _user_response(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, settings: Settings = Depends(get_settings)) -> None:
    response.delete_cookie(settings.cookie_name, path="/")
