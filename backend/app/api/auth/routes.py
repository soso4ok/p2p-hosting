from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user, get_current_user
from app.db.database_connection import get_db
from app.dto.auth import (
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.exceptions.auth_exceptions import (
    AccountSuspendedError,
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
    UserNotFoundError,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register_user(
    user_data: UserCreate, db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """Register a new user."""
    try:
        return await AuthService.register_user(user_data, db)
    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=Token)
async def login_user(
    user_credentials: UserLogin, db: AsyncSession = Depends(get_db)
) -> Token:
    """Authenticate user and return JWT tokens."""
    try:
        return await AuthService.authenticate_user(user_credentials, db)
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except AccountSuspendedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/logout")
async def logout_user(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> dict:
    """Logout current user."""
    await AuthService.logout_user(current_user.id, db)
    return {"message": "Successfully logged out"}


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str, db: AsyncSession = Depends(get_db)
) -> Token:
    """Refresh access token using refresh token."""
    try:
        return await AuthService.refresh_user_token(refresh_token, db)
    except (InvalidTokenError, UserNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """Get current user information."""
    return UserResponse.model_validate(current_user)
