import uuid

import jwt

from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.users.models import User
from app.users.repository import UserRepository
from app.users.schemas import UserCreate


class AuthError(Exception):
    pass


class UserService:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def authenticate(self, email: str, password: str) -> tuple[User, str]:
        user = await self._repo.get_by_email(email)
        if not user or not user.is_active or not verify_password(password, user.password_hash):
            raise AuthError("Credenciales inválidas")
        token = create_access_token(subject=str(user.id))
        return user, token

    async def get_by_token(self, token: str) -> User:
        try:
            user_id_str = decode_token(token)
        except jwt.InvalidTokenError as exc:
            raise AuthError("Sesión inválida o expirada") from exc
        user = await self._repo.get_by_id(uuid.UUID(user_id_str))
        if not user or not user.is_active:
            raise AuthError("Usuario no encontrado o inactivo")
        return user

    async def create_user(self, data: UserCreate) -> User:
        existing = await self._repo.get_by_email(data.email)
        if existing:
            raise ValueError("Ya existe un usuario con ese email")
        return await self._repo.create(
            email=data.email,
            full_name=data.full_name,
            password_hash=hash_password(data.password),
            role=data.role,
        )
