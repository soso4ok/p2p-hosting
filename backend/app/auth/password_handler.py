import secrets
from typing import cast

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class PasswordHandler:
    @staticmethod
    def hash_password(password: str) -> str:
        return cast(str, pwd_context.hash(password))

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return cast(bool, pwd_context.verify(plain_password, hashed_password))

    @staticmethod
    def needs_update(hashed_password: str) -> bool:
        return cast(bool, pwd_context.needs_update(hashed_password))

    @staticmethod
    def generate_password_token() -> str:
        return secrets.token_urlsafe()
