"""Tests unitarios de UserService usando un repositorio falso."""

import uuid
from datetime import datetime, UTC

import pytest

from app.core.security import decode_token, hash_password
from app.users.models import User
from app.users.schemas import UserCreate
from app.users.service import AuthError, UserService


# ── repositorio falso ─────────────────────────────────────────────────────────

class _FakeUserRepository:
    def __init__(self, user: User | None = None) -> None:
        self._store: list[User] = [user] if user else []

    async def get_by_email(self, email: str) -> User | None:
        return next((u for u in self._store if u.email == email), None)

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return next((u for u in self._store if u.id == user_id), None)

    async def create(
        self,
        email: str,
        full_name: str,
        password_hash: str,
        role: str = "analyst",
    ) -> User:
        user = User(
            id=uuid.uuid4(),
            email=email,
            full_name=full_name,
            password_hash=password_hash,
            role=role,
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self._store.append(user)
        return user


def _make_user(email: str = "ana@example.com", password: str = "S3cret!99") -> User:
    return User(
        id=uuid.uuid4(),
        email=email,
        full_name="Ana Gómez",
        password_hash=hash_password(password),
        role="analyst",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


# ── authenticate ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_authenticate_returns_user_and_valid_token() -> None:
    user = _make_user()
    service = UserService(_FakeUserRepository(user))
    returned_user, token = await service.authenticate(user.email, "S3cret!99")
    assert returned_user.email == user.email
    assert decode_token(token) == str(user.id)


@pytest.mark.asyncio
async def test_authenticate_wrong_password_raises() -> None:
    user = _make_user()
    service = UserService(_FakeUserRepository(user))
    with pytest.raises(AuthError):
        await service.authenticate(user.email, "contraseña_incorrecta")


@pytest.mark.asyncio
async def test_authenticate_unknown_email_raises() -> None:
    service = UserService(_FakeUserRepository())
    with pytest.raises(AuthError):
        await service.authenticate("desconocido@example.com", "cualquiera")


@pytest.mark.asyncio
async def test_authenticate_inactive_user_raises() -> None:
    user = _make_user()
    user.is_active = False
    service = UserService(_FakeUserRepository(user))
    with pytest.raises(AuthError):
        await service.authenticate(user.email, "S3cret!99")


# ── get_by_token ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_by_token_returns_user() -> None:
    user = _make_user()
    service = UserService(_FakeUserRepository(user))
    _, token = await service.authenticate(user.email, "S3cret!99")
    fetched = await service.get_by_token(token)
    assert fetched.id == user.id


@pytest.mark.asyncio
async def test_get_by_token_expired_raises() -> None:
    from datetime import timedelta
    from app.core.security import create_access_token

    user = _make_user()
    expired_token = create_access_token(str(user.id), expires_delta=timedelta(seconds=-1))
    service = UserService(_FakeUserRepository(user))
    with pytest.raises(AuthError):
        await service.get_by_token(expired_token)


@pytest.mark.asyncio
async def test_get_by_token_malformed_raises() -> None:
    service = UserService(_FakeUserRepository(_make_user()))
    with pytest.raises(AuthError):
        await service.get_by_token("no.es.un.jwt.valido")


# ── create_user ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_user_stores_hashed_password() -> None:
    repo = _FakeUserRepository()
    service = UserService(repo)
    data = UserCreate(email="nuevo@example.com", full_name="Nuevo Usuario", password="P@ss123!")
    user = await service.create_user(data)
    assert user.email == "nuevo@example.com"
    # contraseña nunca se guarda en texto plano
    assert user.password_hash != "P@ss123!"
    from app.core.security import verify_password
    assert verify_password("P@ss123!", user.password_hash)


@pytest.mark.asyncio
async def test_create_user_duplicate_email_raises() -> None:
    existing = _make_user("dup@example.com")
    repo = _FakeUserRepository(existing)
    service = UserService(repo)
    data = UserCreate(email="dup@example.com", full_name="Otro", password="P@ss123!")
    with pytest.raises(ValueError, match="Ya existe"):
        await service.create_user(data)


@pytest.mark.asyncio
async def test_create_user_default_role_is_analyst() -> None:
    repo = _FakeUserRepository()
    service = UserService(repo)
    data = UserCreate(email="ana2@example.com", full_name="Ana", password="P@ss!")
    user = await service.create_user(data)
    assert user.role == "analyst"
