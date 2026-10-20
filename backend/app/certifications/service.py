from __future__ import annotations

import uuid
from typing import Optional

from app.certifications.models import Certification, STAGE_ORDER
from app.certifications.repository import CertificationRepository
from app.certifications.schemas import CertificationCreate, CertificationUpdate
from app.recipes.repository import RecipeRepository

# Stages that service_rest_json auto-activates when data_origin = factory_request (RF-40c)
_FACTORY_AUTO_STAGES = {"data_request", "assignment"}


class CertificationError(Exception):
    pass


class CertificationService:
    def __init__(self, repo: CertificationRepository, recipe_repo: RecipeRepository) -> None:
        self._repo = repo
        self._recipe_repo = recipe_repo

    async def create(self, owner_id: uuid.UUID, data: CertificationCreate) -> Certification:
        recipe = await self._recipe_repo.get_recipe_by_code(data.recipe_code)
        if recipe is None:
            raise CertificationError(f"Receta no encontrada: {data.recipe_code}")

        active_stages: dict[str, str] = dict(recipe.stages)
        data_origin = data.data_origin or recipe.default_data_origin

        # Auto-activate for service_rest_json + factory_request (RF-40c).
        # Baked into active_stages at creation; no separate events needed
        # because this is the initial state, not a post-creation change.
        if data.recipe_code == "service_rest_json" and data_origin == "factory_request":
            for s in _FACTORY_AUTO_STAGES:
                active_stages[s] = "required"

        return await self._repo.create(
            owner_id=owner_id,
            type=data.type,
            external_code=data.external_code,
            module=data.module,
            title=data.title,
            description=data.description,
            service=data.service,
            recipe_code=data.recipe_code,
            active_stages=active_stages,
            case_style=data.case_style or recipe.default_case_style,
            evidence_style=data.evidence_style or recipe.default_evidence_style,
            execution_channel=data.execution_channel or recipe.default_execution_channel,
            data_origin=data_origin,
        )

    async def get(self, cert_id: uuid.UUID, owner_id: Optional[uuid.UUID]) -> Certification:
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
        recipe_code: Optional[str] = None,
    ) -> list[Certification]:
        return await self._repo.list_by_owner(
            owner_id, type=type, module=module, stage=stage,
            status=status, recipe_code=recipe_code,
        )

    async def update(
        self, cert_id: uuid.UUID, owner_id: Optional[uuid.UUID], data: CertificationUpdate
    ) -> Certification:
        cert = await self.get(cert_id, owner_id)
        updates = {k: v for k, v in data.model_dump().items() if v is not None}
        if not updates:
            return cert

        # ── Handle data_origin change for service_rest_json (RF-40c, point 4) ──
        new_origin = updates.pop("data_origin", None)
        if new_origin and cert.recipe_code == "service_rest_json" and cert.active_stages:
            stages = dict(cert.active_stages)
            promoted: list[str] = []
            demoted: list[str] = []

            if new_origin == "factory_request":
                for s in _FACTORY_AUTO_STAGES:
                    if stages.get(s) != "required":
                        stages[s] = "required"
                        promoted.append(s)
            else:
                recipe = await self._recipe_repo.get_recipe_by_code(cert.recipe_code)
                for s in _FACTORY_AUTO_STAGES:
                    if stages.get(s) == "required":
                        # Restore to recipe default (typically "optional")
                        stages[s] = recipe.stages.get(s, "optional") if recipe else "optional"
                        demoted.append(s)

            # Always persist the origin change
            updates["data_origin"] = new_origin
            if promoted or demoted:
                # Persist active_stages + origin together, with source="origin" events
                updates["active_stages"] = stages
                cert = await self._repo.apply_origin_stage_changes(
                    cert, stages, promoted, demoted
                )
                # Remove active_stages from generic update to avoid double-write
                updates.pop("active_stages", None)

        if updates:
            cert = await self._repo.update_fields(cert, **updates)
        return cert

    def _active_stage_list(self, cert: Certification) -> list[str]:
        """Ordered list of stages that are required or optional."""
        if not cert.active_stages:
            return STAGE_ORDER
        return [s for s in STAGE_ORDER if cert.active_stages.get(s) in ("required", "optional")]

    async def change_stage(
        self, cert_id: uuid.UUID, owner_id: Optional[uuid.UUID], direction: str
    ) -> Certification:
        cert = await self.get(cert_id, owner_id)
        if cert.status == "closed":
            raise CertificationError("La certificación ya está cerrada")

        active = self._active_stage_list(cert)
        if cert.stage not in active:
            raise CertificationError(f"La etapa actual '{cert.stage}' no está en las etapas activas")

        current_idx = active.index(cert.stage)
        if direction == "forward":
            if current_idx == len(active) - 1:
                raise CertificationError("La certificación ya está en la etapa final")
            new_stage = active[current_idx + 1]
        elif direction == "back":
            if current_idx == 0:
                raise CertificationError("No se puede retroceder desde la primera etapa")
            if cert.stage == "closed":
                raise CertificationError("No se puede retroceder una certificación cerrada")
            new_stage = active[current_idx - 1]
        else:
            raise CertificationError(f"Dirección inválida: {direction}")

        return await self._repo.update_stage(cert, new_stage)

    async def add_stage(
        self, cert_id: uuid.UUID, owner_id: Optional[uuid.UUID], stage: str
    ) -> Certification:
        if stage not in STAGE_ORDER:
            raise CertificationError(f"Etapa no válida: {stage}")
        cert = await self.get(cert_id, owner_id)
        if cert.status == "closed":
            raise CertificationError("La certificación está cerrada")
        current = cert.active_stages or {}
        if current.get(stage) in ("required", "optional"):
            raise CertificationError(f"La etapa '{stage}' ya está activa")
        return await self._repo.add_stage(cert, stage)

    async def remove_stage(
        self, cert_id: uuid.UUID, owner_id: Optional[uuid.UUID], stage: str
    ) -> Certification:
        if stage not in STAGE_ORDER:
            raise CertificationError(f"Etapa no válida: {stage}")
        cert = await self.get(cert_id, owner_id)
        if cert.status == "closed":
            raise CertificationError("La certificación está cerrada")
        current = cert.active_stages or {}

        if current.get(stage) == "not_applicable":
            raise CertificationError(f"La etapa '{stage}' ya está inactiva")
        # Current stage check before required: an in-flight stage cannot be removed
        # regardless of whether it is required or optional (point 5)
        if cert.stage == stage:
            raise CertificationError(f"No se puede quitar la etapa en curso: '{stage}'")
        if current.get(stage) == "required":
            raise CertificationError(f"No se puede quitar una etapa requerida: {stage}")
        if await self._repo.stage_has_data(cert.id, stage):
            raise CertificationError(
                f"La etapa '{stage}' ya tiene datos asociados; elimínalos primero"
            )
        return await self._repo.remove_stage(cert, stage)
