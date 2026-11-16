"""
Authentication service.
Handles user registration, login, and token operations.
All database operations go through the ORM — no raw SQL.
"""
from __future__ import annotations

import uuid
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, ConflictError
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import RegisterRequest, TokenResponse

logger = get_logger(__name__)


def register_user(db: Session, payload: RegisterRequest) -> User:
    """Create a new user. Raises ConflictError if email already exists."""
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise ConflictError(f"An account with email '{payload.email}' already exists.")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role="analyst",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("New user registered", extra={"user_id": str(user.id)})
    return user


def login_user(db: Session, email: str, password: str) -> TokenResponse:
    """Validate credentials and return a token pair."""
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise AuthenticationError("Invalid email or password.")
    if not user.is_active:
        raise AuthenticationError("Account is deactivated.")

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))
    logger.info("User logged in", extra={"user_id": str(user.id)})
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=3600,
    )


def refresh_tokens(db: Session, refresh_token: str) -> TokenResponse:
    """Validate a refresh token and issue a new token pair."""
    from jose import JWTError
    try:
        payload = decode_token(refresh_token)
    except JWTError:
        raise AuthenticationError("Invalid or expired refresh token.")

    if payload.get("type") != "refresh":
        raise AuthenticationError("Token is not a refresh token.")

    user_id_str = payload.get("sub")
    try:
        user_id = uuid.UUID(user_id_str)
    except (ValueError, TypeError):
        raise AuthenticationError("Invalid user ID in token.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise AuthenticationError("User not found or deactivated.")

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
        expires_in=3600,
    )


def get_current_user_from_token(db: Session, token: str) -> User:
    """Extract and validate the current user from a Bearer token."""
    from jose import JWTError
    try:
        payload = decode_token(token)
    except JWTError:
        raise AuthenticationError("Invalid or expired access token.")

    if payload.get("type") != "access":
        raise AuthenticationError("Token is not an access token.")

    user_id_str = payload.get("sub")
    try:
        user_id = uuid.UUID(user_id_str)
    except (ValueError, TypeError):
        raise AuthenticationError("Invalid user ID in token.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise AuthenticationError("User not found or deactivated.")
    return user
