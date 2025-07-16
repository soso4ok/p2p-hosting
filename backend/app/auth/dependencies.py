from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_handler import JWTHandler
from app.db.database_connection import get_db
from app.dto.auth import TokenData
from app.models.user import User, UserRole, UserStatus

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    token_data: Optional[TokenData] = JWTHandler.verify_token(token)

    if token_data is None or token_data.user_id is None:
        raise credentials_exception

    stmt = select(User).where(User.id == token_data.user_id)
    result = await db.execute(stmt)
    user: Optional[User] = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is not active"
        )
    return current_user


async def get_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return current_user


async def get_host_user(current_user: User = Depends(get_current_active_user)) -> User:
    if current_user.role not in [UserRole.HOST, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Host access required"
        )
    return current_user


def require_roles(*allowed_roles: UserRole):
    async def role_checker(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}",
            )
        return current_user

    return role_checker


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    if not credentials:
        return None

    try:
        token = credentials.credentials
        token_data: Optional[TokenData] = JWTHandler.verify_token(token)

        if token_data is None or token_data.user_id is None:
            return None

        # Get user from database
        stmt = select(User).where(User.id == token_data.user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None or user.status != UserStatus.ACTIVE:
            return None

        return user

    except Exception:
        return None
