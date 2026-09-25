from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import clear_auth_cookie, set_auth_cookie
from app.users.models import User, UserApiKey
from app.users.repository import UserRepository
from app.users.schemas import LlmConfigIn, LlmConfigOut, LoginRequest, UserRead
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


@router.put("/me/llm-config", response_model=LlmConfigOut)
async def save_llm_config(
    body: LlmConfigIn,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> LlmConfigOut:
    from app.core.crypto import encrypt
    encrypted = encrypt(body.api_key)
    result = await session.execute(
        select(UserApiKey).where(
            UserApiKey.user_id == current_user.id,
            UserApiKey.provider == body.provider,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        row.encrypted_key = encrypted
        row.model = body.model
        row.base_url = body.base_url
    else:
        row = UserApiKey(
            user_id=current_user.id,
            provider=body.provider,
            encrypted_key=encrypted,
            model=body.model,
            base_url=body.base_url,
        )
        session.add(row)
    await session.commit()
    return LlmConfigOut(
        provider=row.provider,
        model=row.model,
        base_url=row.base_url,
        key_hint=f"...{body.api_key[-4:]}",
    )


@router.get("/me/llm-config", response_model=list[LlmConfigOut])
async def get_llm_config(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[LlmConfigOut]:
    result = await session.execute(
        select(UserApiKey).where(UserApiKey.user_id == current_user.id)
    )
    rows = result.scalars().all()
    from app.core.crypto import decrypt
    configs = []
    for r in rows:
        try:
            raw = decrypt(r.encrypted_key)
            hint = f"...{raw[-4:]}"
        except Exception:
            hint = "...????"
        configs.append(LlmConfigOut(provider=r.provider, model=r.model, base_url=r.base_url, key_hint=hint))
    return configs


@router.delete("/me/llm-config/{provider}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_llm_config(
    provider: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    result = await session.execute(
        select(UserApiKey).where(
            UserApiKey.user_id == current_user.id,
            UserApiKey.provider == provider,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        await session.delete(row)
        await session.commit()


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
