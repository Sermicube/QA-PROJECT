import uuid
from pathlib import Path

from app.core.config import settings


def _base() -> Path:
    return Path(settings.FILES_DIR)


def cert_dir(certification_id: uuid.UUID) -> Path:
    d = _base() / str(certification_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_upload(certification_id: uuid.UUID, original_name: str, data: bytes) -> tuple[str, str]:
    """Persist uploaded bytes. Returns (file_path, stored_file_name)."""
    suffix = Path(original_name).suffix.lower()
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    dest = cert_dir(certification_id) / stored_name
    dest.write_bytes(data)
    return str(dest), stored_name


def delete_file(file_path: str) -> None:
    p = Path(file_path)
    if p.exists():
        p.unlink()
