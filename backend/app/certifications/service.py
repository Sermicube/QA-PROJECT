import uuid
from typing import Optional

from app.certifications.models import Certification, STAGE_ORDER
from app.certifications.repository import CertificationRepository
from app.certifications.schemas import CertificationCreate, CertificationUpdate


class CertificationError(Exception):
    pass


class CertificationService:
    def __init__(self, repo: CertificationRepository) -> None:
        self._repo = repo

    async def create(
        self, owner_id: uuid.UUID, data: CertificationCreate
    ) -> Certification:
        return await self._repo.create(
            owner_id=owner_id,
            type=data.type,
            external_code=data.external_code,
            module=data.module,
            title=data.title,
            description=data.description,
        )

    async def get(
        self, cert_id: uuid.UUID, owner_id: uuid.UUID | None
    ) -> Certification:
        cert = await self._repo.get_by_id(cert_id, owner_id=owner_id)
        if cert is None:
            raise CertificationError("Certificación no encontrada")
        return cert

    async def list(
        self,
        owner_id: uuid.UUID,
        *,
        type: Optional[str] = None,
        module: Optional[str] = None,
        stage: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[Certification]:
        return await self._repo.list_by_owner(
            owner_id, type=type, module=module, stage=stage, status=status
        )

    async def update(
        self, cert_id: uuid.UUID, owner_id: uuid.UUID | None, data: CertificationUpdate
    ) -> Certification:
        cert = await self.get(cert_id, owner_id)
        updates = {k: v for k, v in data.model_dump().items() if v is not None}
        if not updates:
            return cert
        return await self._repo.update_fields(cert, **updates)

    async def change_stage(
        self, cert_id: uuid.UUID, owner_id: uuid.UUID | None, direction: str
    ) -> Certification:
        cert = await self.get(cert_id, owner_id)
        if cert.status == "closed":
            raise CertificationError("La certificación ya está cerrada")

        current_idx = STAGE_ORDER.index(cert.stage)
        if direction == "forward":
            if current_idx == len(STAGE_ORDER) - 1:
                raise CertificationError("La certificación ya está en la etapa final")
            new_stage = STAGE_ORDER[current_idx + 1]
        elif direction == "back":
            if current_idx == 0:
                raise CertificationError("No se puede retroceder desde la primera etapa")
            if cert.stage == "closed":
                raise CertificationError("No se puede retroceder una certificación cerrada")
            new_stage = STAGE_ORDER[current_idx - 1]
        else:
            raise CertificationError(f"Dirección inválida: {direction}")

        return await self._repo.update_stage(cert, new_stage)
