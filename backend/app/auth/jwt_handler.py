import os
from datetime import datetime, timedelta, timezone
from typing import Optional, cast
from uuid import UUID

from jose import JWTError, jwt

from app.dto.auth import TokenData

# temporaty solution for secret key management
SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "QpSMXtDcceqibAnIHcw82YDw6QbjzYrTLI62TM8UeUT5Za3uYekwjgPinVPSFQWOjB+uZzO7/+AdFqrw9uEXDw==",
)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", 7))


class JWTHandler:

    @staticmethod
    def create_access_token(
        data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=ACCESS_TOKEN_EXPIRE_MINUTES
            )
        to_encode.update(
            {"exp": expire, "iat": datetime.now(timezone.utc), "type": "access"}
        )

        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return cast(str, encoded_jwt)

    @staticmethod
    def create_refresh_token(data: dict) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        to_encode.update(
            {"exp": expire, "iat": datetime.now(timezone.utc), "type": "refresh"}
        )

        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return cast(str, encoded_jwt)

    @staticmethod
    def verify_token(token: str) -> Optional[TokenData]:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

            user_id_str: str = payload.get("sub")
            if user_id_str is None:
                return None

            user_id = UUID(user_id_str)
            username: str = payload.get("username")
            email: str = payload.get("email")
            role: str = payload.get("role")

            token_data = TokenData(
                user_id=user_id, username=username, email=email, role=role
            )
            return token_data

        except (JWTError, ValueError):
            return None

    @staticmethod
    def verify_refresh_token(token: str) -> Optional[TokenData]:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

            # Check if it's a refresh token
            token_type = payload.get("type")
            if token_type != "refresh":
                return None

            user_id_str: str = payload.get("sub")
            if user_id_str is None:
                return None

            user_id = UUID(user_id_str)
            username: str = payload.get("username")
            email: str = payload.get("email")
            role: str = payload.get("role")

            token_data = TokenData(
                user_id=user_id, username=username, email=email, role=role
            )
            return token_data

        except (JWTError, ValueError):
            return None

    @staticmethod
    def create_token_pair(user_data: dict) -> dict:
        access_token = JWTHandler.create_access_token(data=user_data)
        refresh_token = JWTHandler.create_refresh_token(data=user_data)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    @staticmethod
    def get_token_expiry(token: str) -> Optional[datetime]:
        try:
            payload = jwt.decode(
                token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False}
            )
            exp_timestamp = payload.get("exp")
            if exp_timestamp:
                return datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            return None
        except JWTError:
            return None
