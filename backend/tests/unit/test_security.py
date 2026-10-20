from datetime import timedelta

import jwt as pyjwt
import pytest
from fastapi import FastAPI, Response
from fastapi.testclient import TestClient

from app.core.security import (
    clear_auth_cookie,
    create_access_token,
    decode_token,
    hash_password,
    set_auth_cookie,
    verify_password,
)


def test_hash_verify_roundtrip() -> None:
    hashed = hash_password("s3cr3t_P@ss")
    assert verify_password("s3cr3t_P@ss", hashed)


def test_verify_wrong_password() -> None:
    hashed = hash_password("s3cr3t_P@ss")
    assert not verify_password("wrong-password", hashed)


def test_create_and_decode_token() -> None:
    token = create_access_token(subject="user-uuid-123")
    subject = decode_token(token)
    assert subject == "user-uuid-123"


def test_expired_token_raises() -> None:
    token = create_access_token(
        subject="user-uuid", expires_delta=timedelta(seconds=-1)
    )
    with pytest.raises(pyjwt.ExpiredSignatureError):
        decode_token(token)


def test_set_auth_cookie_flags_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    """En desarrollo Secure=False y SameSite=lax para permitir HTTP local."""
    from app.core import security as sec_mod
    from app.core.config import Settings

    dev_settings = Settings(APP_ENV="development")
    monkeypatch.setattr(sec_mod, "settings", dev_settings)

    app = FastAPI()

    @app.get("/test-cookie")
    async def endpoint(response: Response) -> dict[str, str]:
        sec_mod.set_auth_cookie(response, "tok")
        return {}

    with TestClient(app) as client:
        resp = client.get("/test-cookie")

    sc = resp.headers.get("set-cookie", "")
    assert "access_token=tok" in sc
    assert "HttpOnly" in sc
    assert "Secure" not in sc
    assert "SameSite=lax" in sc


def test_set_auth_cookie_flags_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    """En producción Secure=True y SameSite=lax."""
    from app.core import security as sec_mod
    from app.core.config import Settings

    prod_settings = Settings(APP_ENV="production")
    monkeypatch.setattr(sec_mod, "settings", prod_settings)

    app = FastAPI()

    @app.get("/test-cookie")
    async def endpoint(response: Response) -> dict[str, str]:
        sec_mod.set_auth_cookie(response, "tok")
        return {}

    with TestClient(app) as client:
        resp = client.get("/test-cookie")

    sc = resp.headers.get("set-cookie", "")
    assert "access_token=tok" in sc
    assert "HttpOnly" in sc
    assert "Secure" in sc
    assert "SameSite=lax" in sc


def test_clear_auth_cookie() -> None:
    app = FastAPI()

    @app.get("/test-clear")
    async def endpoint(response: Response) -> dict[str, str]:
        clear_auth_cookie(response)
        return {}

    with TestClient(app) as client:
        resp = client.get("/test-clear")

    sc = resp.headers.get("set-cookie", "")
    assert "access_token" in sc
    assert "HttpOnly" in sc
