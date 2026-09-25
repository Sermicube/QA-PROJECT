from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import clear_auth_cookie, set_auth_cookie
from app.users.models import User
from app.users.repository import UserRepository
from app.users.schemas import LoginRequest, UserRead
from app.users.service import AuthError, UserService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _service(session: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(UserRepository(session))


@router.post("/login", response_model=UserRead)
async def login(
    body: LoginRequest,
    response: Response,
    service: UserService = Depends(_service),
) -> UserRead:
    try:
        user, token = await service.authenticate(body.email, body.password)
    except AuthError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
    set_auth_cookie(response, token)
    return UserRead.model_validate(user)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(response: Response) -> dict[str, str]:
    clear_auth_cookie(response)
    return {"message": "Sesión cerrada"}


async def get_current_user(
    access_token: str | None = Cookie(default=None),
    service: UserService = Depends(_service),
) -> User:
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
    try:
        return await service.get_by_token(access_token)
    except AuthError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida o expirada")


@router.get("/me", response_model=UserRead)
async def me(
    access_token: str | None = Cookie(default=None),
    service: UserService = Depends(_service),
) -> UserRead:
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
    try:
        user = await service.get_by_token(access_token)
    except AuthError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida o expirada")
    return UserRead.model_validate(user)
