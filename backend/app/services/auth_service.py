from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import EmailStr
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_handler import ACCESS_TOKEN_EXPIRE_MINUTES, JWTHandler
from app.auth.password_handler import PasswordHandler
from app.dto.auth import Token, UserCreate, UserLogin, UserResponse
from app.models.user import User, UserPreferences, UserSession, UserStatus
from app.services.exceptions.auth_exceptions import (
    AccountSuspendedError,
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
    UserNotFoundError,
)


class AuthService:
    """Service class handling authentication business logic."""

    @staticmethod
    async def register_user(user_data: UserCreate, db: AsyncSession) -> UserResponse:

        if await AuthService._user_exists(user_data.email, user_data.username, db):
            raise UserAlreadyExistsError("Email or username already registered")

        # Hash password
        hashed_password = PasswordHandler.hash_password(user_data.password)

        # Create user
        new_user = User(
            email=user_data.email,
            username=user_data.username,
            password_hash=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            display_name=user_data.display_name or user_data.username,
            bio=user_data.bio,
        )

        try:
            db.add(new_user)
            await db.flush()

            # Create default preferences
            preferences = UserPreferences(user_id=new_user.id)
            db.add(preferences)

            await db.commit()
            await db.refresh(new_user)

            return UserResponse.model_validate(new_user)

        except IntegrityError:
            await db.rollback()
            raise UserAlreadyExistsError("Email or username already registered")

    @staticmethod
    async def authenticate_user(credentials: UserLogin, db: AsyncSession) -> Token:
        user = await AuthService._get_user_by_email(credentials.email, db)
        if not user:
            raise InvalidCredentialsError("Incorrect email or password")

        # Verify password
        if not PasswordHandler.verify_password(
            credentials.password, str(user.password_hash)
        ):
            raise InvalidCredentialsError("Incorrect email or password")

        # Check account status
        if user.status == UserStatus.SUSPENDED:
            raise AccountSuspendedError("Account is suspended")

        # Update last login
        user.last_login_at = datetime.now(timezone.utc)

        # Create tokens
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role,
        }

        tokens = JWTHandler.create_token_pair(token_data)

        # Create session
        await AuthService._create_user_session(user.id, tokens, db)

        await db.commit()

        return Token(**tokens)

    @staticmethod
    async def logout_user(user_id: UUID, db: AsyncSession) -> None:
        stmt = select(UserSession).where(
            (UserSession.user_id == user_id) & UserSession.is_active
        )
        result = await db.execute(stmt)
        sessions = result.scalars().all()

        for session in sessions:
            session.is_active = False

        await db.commit()

    @staticmethod
    async def refresh_user_token(refresh_token: str, db: AsyncSession) -> Token:
        token_data = JWTHandler.verify_refresh_token(refresh_token)
        if not token_data or not token_data.user_id:
            raise InvalidTokenError("Invalid refresh token")

        # Find active session
        session = await AuthService._get_active_session_by_refresh_token(
            refresh_token, db
        )
        if not session:
            raise InvalidTokenError("Invalid or expired refresh token")

        # Get user
        user = await AuthService._get_user_by_id(token_data.user_id, db)
        if not user or user.status != UserStatus.ACTIVE:
            raise UserNotFoundError("User not found or inactive")

        # Create new token pair
        new_token_data = {
            "sub": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role,
        }

        tokens = JWTHandler.create_token_pair(new_token_data)

        # Update session
        session.session_token = tokens["access_token"][-32:]
        session.refresh_token = tokens["refresh_token"]
        session.expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
        session.last_activity_at = datetime.now(timezone.utc)

        await db.commit()

        return Token(**tokens)

    # Private helper methods
    @staticmethod
    async def _user_exists(email: EmailStr, username: str, db: AsyncSession) -> bool:
        stmt = select(User).where((User.email == email) | (User.username == username))
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def _get_user_by_email(email: EmailStr, db: AsyncSession) -> Optional[User]:
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def _get_user_by_id(user_id: UUID, db: AsyncSession) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def _create_user_session(
        user_id: UUID, tokens: Dict[str, Any], db: AsyncSession
    ) -> None:
        session = UserSession(
            user_id=user_id,
            session_token=tokens["access_token"][-32:],
            refresh_token=tokens["refresh_token"],
            expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        db.add(session)

    @staticmethod
    async def _get_active_session_by_refresh_token(
        refresh_token: str, db: AsyncSession
    ) -> Optional[UserSession]:
        stmt = select(UserSession).where(
            (UserSession.refresh_token == refresh_token) & UserSession.is_active
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
