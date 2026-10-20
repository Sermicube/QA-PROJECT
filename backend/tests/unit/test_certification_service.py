"""Unit tests for CertificationService — RF-01, RF-01b, RF-01c, RF-01d."""

import uuid
from datetime import UTC, datetime
from typing import Optional

import pytest

from app.certifications.models import Certification, STAGE_ORDER, StageEvent
from app.certifications.schemas import CertificationCreate, CertificationUpdate
from app.certifications.service import CertificationError, CertificationService
from app.recipes.models import Recipe


# ── fake repos ────────────────────────────────────────────────────────────────

_BUG_SIMPLE_STAGES = {
    "context": "required", "testcases": "required", "format": "required",
    "data_request": "not_applicable", "assignment": "not_applicable",
    "execution": "required", "analysis": "not_applicable",
    "documentation": "required", "review": "required", "closed": "required",
}

_REST_JSON_STAGES = {
    "context": "required", "testcases": "required", "format": "required",
    "data_request": "optional", "assignment": "optional",
    "execution": "required", "analysis": "required",
    "documentation": "required", "review": "required", "closed": "required",
}

_BRECHA_DATE_STAGES = {
    "context": "required", "testcases": "required", "format": "required",
    "data_request": "optional", "assignment": "optional",
    "execution": "required", "analysis": "not_applicable",
    "documentation": "required", "review": "required", "closed": "required",
}

_ALL_REQUIRED_STAGES = {s: "required" for s in [
    "context", "testcases", "format", "data_request", "assignment",
    "execution", "analysis", "documentation", "review", "closed",
]}

def _make_recipe(code: str, name: str, stages: dict, style: str, channel: str, origin: str,
                 evidence_style: str = "default", pattern: str = "one_case") -> Recipe:
    return Recipe(
        id=uuid.uuid4(), code=code, name=name, description="",
        stages=stages, default_case_style=style, default_evidence_style=evidence_style,
        default_execution_channel=channel, default_data_origin=origin,
        suggested_case_pattern=pattern, is_builtin=True,
    )

_BUILTIN_RECIPES = {
    "bug_simple": _make_recipe("bug_simple", "Bug — un caso", _BUG_SIMPLE_STAGES, "short", "ui", "developer_case"),
    "bug_before_after": _make_recipe("bug_before_after", "Bug — antes/después", _BUG_SIMPLE_STAGES, "short", "ui", "developer_case", evidence_style="before_after", pattern="before_after"),
    "bug_negative_control": _make_recipe("bug_negative_control", "Bug — negativo + control", _BUG_SIMPLE_STAGES, "short", "ui", "colleague_request", pattern="negative_control"),
    "brecha_date_rule": _make_recipe("brecha_date_rule", "Brecha con regla de fecha", _BRECHA_DATE_STAGES, "validate_that", "ui", "colleague_request", pattern="boundary"),
    "service_soap_xml": _make_recipe("service_soap_xml", "Servicio SOAP/XML", _ALL_REQUIRED_STAGES, "consult_service", "soap_xml", "factory_request", evidence_style="service_blocks", pattern="matrix_by_role"),
    "service_rest_json": _make_recipe("service_rest_json", "Servicio REST/JSON", _REST_JSON_STAGES, "consult_service", "rest_json", "manual_search", evidence_style="service_blocks", pattern="matrix_by_role"),
    "file_batch": _make_recipe("file_batch", "Cargue de archivo", _BUG_SIMPLE_STAGES, "action_validations", "file_upload", "client_file"),
    "client_cases": _make_recipe("client_cases", "Casos del cliente", _BUG_SIMPLE_STAGES, "validate_that", "ui", "client_file", pattern="client_cases"),
}


class _FakeRecipeRepo:
    async def get_recipe_by_code(self, code: str) -> Optional[Recipe]:
        return _BUILTIN_RECIPES.get(code)


class _FakeCertRepo:
    def __init__(self) -> None:
        self._store: list[Certification] = []
        self._stage_data: dict[tuple[uuid.UUID, str], bool] = {}

    def set_stage_data(self, cert_id: uuid.UUID, stage: str, has_data: bool) -> None:
        self._stage_data[(cert_id, stage)] = has_data

    async def stage_has_data(self, cert_id: uuid.UUID, stage: str) -> bool:
        return self._stage_data.get((cert_id, stage), False)

    async def apply_origin_stage_changes(self, cert, new_stages, promoted_stages, demoted_stages):
        cert.active_stages = new_stages
        now = datetime.now(UTC)
        for stage in promoted_stages:
            cert.stage_events.append(StageEvent(
                id=uuid.uuid4(), certification_id=cert.id, stage=stage,
                status="stage_added", source="origin", started_at=now,
            ))
        for stage in demoted_stages:
            cert.stage_events.append(StageEvent(
                id=uuid.uuid4(), certification_id=cert.id, stage=stage,
                status="stage_removed", source="origin", started_at=now,
            ))
        return cert

    async def create(self, owner_id, type, external_code, module, title, **kw) -> Certification:
        now = datetime.now(UTC)
        cert = Certification(
            id=uuid.uuid4(), owner_id=owner_id, type=type,
            external_code=external_code, module=module, title=title,
            description=kw.get("description"),
            service=kw.get("service"),
            recipe_code=kw.get("recipe_code"),
            active_stages=kw.get("active_stages"),
            case_style=kw.get("case_style"),
            evidence_style=kw.get("evidence_style"),
            execution_channel=kw.get("execution_channel"),
            data_origin=kw.get("data_origin"),
            stage="context", status="active",
            created_at=now, updated_at=now,
        )
        cert.stage_events = [
            StageEvent(id=uuid.uuid4(), certification_id=cert.id, stage="context",
                       status="executed", source="recipe", started_at=now)
        ]
        self._store.append(cert)
        return cert

    async def get_by_id(self, cert_id, owner_id=None):
        for c in self._store:
            if c.id == cert_id and (owner_id is None or c.owner_id == owner_id):
                return c
        return None

    async def list_by_owner(self, owner_id, *, type=None, module=None, stage=None, status=None, recipe_code=None):
        res = [c for c in self._store if c.owner_id == owner_id]
        if type:
            res = [c for c in res if c.type == type]
        if recipe_code:
            res = [c for c in res if c.recipe_code == recipe_code]
        return res

    async def update_stage(self, cert, new_stage):
        now = datetime.now(UTC)
        for ev in cert.stage_events:
            if ev.stage == cert.stage and ev.ended_at is None:
                ev.ended_at = now
                ev.status = "executed"
        cert.stage = new_stage
        if new_stage == "closed":
            cert.status = "closed"
            cert.closed_at = now
        cert.stage_events.append(
            StageEvent(id=uuid.uuid4(), certification_id=cert.id, stage=new_stage,
                       status="executed", source="recipe", started_at=now)
        )
        return cert

    async def add_stage(self, cert, stage):
        cert.active_stages = {**(cert.active_stages or {}), stage: "optional"}
        cert.stage_events.append(
            StageEvent(id=uuid.uuid4(), certification_id=cert.id, stage=stage,
                       status="stage_added", source="analyst", started_at=datetime.now(UTC))
        )
        return cert

    async def remove_stage(self, cert, stage):
        cert.active_stages = {**(cert.active_stages or {}), stage: "not_applicable"}
        cert.stage_events.append(
            StageEvent(id=uuid.uuid4(), certification_id=cert.id, stage=stage,
                       status="stage_removed", source="analyst", started_at=datetime.now(UTC))
        )
        return cert

    async def update_active_stages(self, cert, active_stages):
        cert.active_stages = active_stages
        return cert

    async def update_fields(self, cert, **kwargs):
        for k, v in kwargs.items():
            setattr(cert, k, v)
        return cert


def _svc() -> CertificationService:
    return CertificationService(_FakeCertRepo(), _FakeRecipeRepo())


def _svc_with_repo() -> tuple[CertificationService, _FakeCertRepo]:
    repo = _FakeCertRepo()
    return CertificationService(repo, _FakeRecipeRepo()), repo


_OWNER = uuid.uuid4()
_CREATE_BUG = CertificationCreate(
    type="bug", external_code="BUG-001", module="Novedades",
    title="Bug simple", recipe_code="bug_simple",
)
_CREATE_REST = CertificationCreate(
    type="brecha", external_code="BRE-990", module="API",
    title="Brecha 990", recipe_code="service_rest_json",
)


# ── create copies active_stages from recipe (RF-01c) ─────────────────────────

@pytest.mark.asyncio
async def test_create_copies_active_stages_from_recipe() -> None:
    cert = await _svc().create(_OWNER, _CREATE_BUG)
    assert cert.active_stages == _BUG_SIMPLE_STAGES


@pytest.mark.asyncio
async def test_create_sets_recipe_code() -> None:
    cert = await _svc().create(_OWNER, _CREATE_BUG)
    assert cert.recipe_code == "bug_simple"


@pytest.mark.asyncio
async def test_create_sets_defaults_from_recipe() -> None:
    cert = await _svc().create(_OWNER, _CREATE_BUG)
    assert cert.case_style == "short"
    assert cert.execution_channel == "ui"
    assert cert.data_origin == "developer_case"


@pytest.mark.asyncio
async def test_create_unknown_recipe_raises() -> None:
    svc = _svc()
    with pytest.raises(CertificationError, match="Receta no encontrada"):
        await svc.create(_OWNER, CertificationCreate(
            type="bug", external_code="X", module="M", title="T", recipe_code="no_existe"
        ))


@pytest.mark.asyncio
async def test_create_opens_first_stage_event() -> None:
    cert = await _svc().create(_OWNER, _CREATE_BUG)
    assert len(cert.stage_events) == 1
    ev = cert.stage_events[0]
    assert ev.stage == "context"
    assert ev.status == "executed"
    assert ev.source == "recipe"
    assert ev.ended_at is None


# ── service_rest_json + factory_request auto-activates stages (RF-40c) ────────

@pytest.mark.asyncio
async def test_rest_json_factory_request_activates_data_stages() -> None:
    svc = _svc()
    cert = await svc.create(_OWNER, CertificationCreate(
        type="brecha", external_code="B", module="API", title="T",
        recipe_code="service_rest_json", data_origin="factory_request",
    ))
    assert cert.active_stages["data_request"] == "required"
    assert cert.active_stages["assignment"] == "required"


@pytest.mark.asyncio
async def test_rest_json_manual_search_keeps_optional() -> None:
    cert = await _svc().create(_OWNER, _CREATE_REST)
    assert cert.active_stages["data_request"] == "optional"
    assert cert.active_stages["assignment"] == "optional"


# ── change_stage uses active_stages not STAGE_ORDER (RF-01b) ──────────────────

@pytest.mark.asyncio
async def test_bug_simple_skips_not_applicable_stages() -> None:
    svc = _svc()
    cert = await svc.create(_OWNER, _CREATE_BUG)
    assert cert.stage == "context"
    cert = await svc.change_stage(cert.id, _OWNER, "forward")
    assert cert.stage == "testcases"   # skips nothing between context and testcases
    cert = await svc.change_stage(cert.id, _OWNER, "forward")
    assert cert.stage == "format"
    cert = await svc.change_stage(cert.id, _OWNER, "forward")
    assert cert.stage == "execution"   # data_request and assignment are not_applicable


@pytest.mark.asyncio
async def test_advance_from_last_active_stage_raises() -> None:
    svc = _svc()
    cert = await svc.create(_OWNER, _CREATE_BUG)
    # bug_simple active stages: context, testcases, format, execution, documentation, review, closed
    active = [s for s in STAGE_ORDER if _BUG_SIMPLE_STAGES.get(s) in ("required", "optional")]
    for _ in range(len(active) - 1):
        cert = await svc.change_stage(cert.id, _OWNER, "forward")
    assert cert.stage == "closed"
    with pytest.raises(CertificationError):
        await svc.change_stage(cert.id, _OWNER, "forward")


@pytest.mark.asyncio
async def test_go_back_from_first_stage_raises() -> None:
    svc = _svc()
    cert = await svc.create(_OWNER, _CREATE_BUG)
    with pytest.raises(CertificationError):
        await svc.change_stage(cert.id, _OWNER, "back")


@pytest.mark.asyncio
async def test_closed_sets_status_and_closed_at() -> None:
    svc = _svc()
    cert = await svc.create(_OWNER, _CREATE_BUG)
    active = [s for s in STAGE_ORDER if _BUG_SIMPLE_STAGES.get(s) in ("required", "optional")]
    for _ in range(len(active) - 1):
        cert = await svc.change_stage(cert.id, _OWNER, "forward")
    assert cert.status == "closed"
    assert cert.closed_at is not None


# ── add_stage / remove_stage (RF-01d) ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_optional_stage_activates_it() -> None:
    svc = _svc()
    cert = await svc.create(_OWNER, _CREATE_BUG)
    assert cert.active_stages.get("data_request") == "not_applicable"
    cert = await svc.add_stage(cert.id, _OWNER, "data_request")
    assert cert.active_stages["data_request"] == "optional"


@pytest.mark.asyncio
async def test_add_stage_records_stage_added_event() -> None:
    svc = _svc()
    cert = await svc.create(_OWNER, _CREATE_BUG)
    cert = await svc.add_stage(cert.id, _OWNER, "data_request")
    ev = next((e for e in cert.stage_events if e.status == "stage_added"), None)
    assert ev is not None
    assert ev.stage == "data_request"
    assert ev.source == "analyst"


@pytest.mark.asyncio
async def test_add_already_active_stage_raises() -> None:
    svc = _svc()
    cert = await svc.create(_OWNER, _CREATE_BUG)
    with pytest.raises(CertificationError):
        await svc.add_stage(cert.id, _OWNER, "context")


@pytest.mark.asyncio
async def test_remove_optional_stage_deactivates_it() -> None:
    svc = _svc()
    cert = await svc.create(_OWNER, _CREATE_REST)   # data_request is optional
    cert = await svc.remove_stage(cert.id, _OWNER, "data_request")
    assert cert.active_stages["data_request"] == "not_applicable"


@pytest.mark.asyncio
async def test_remove_optional_stage_records_event() -> None:
    svc = _svc()
    cert = await svc.create(_OWNER, _CREATE_REST)
    cert = await svc.remove_stage(cert.id, _OWNER, "data_request")
    ev = next((e for e in cert.stage_events if e.status == "stage_removed"), None)
    assert ev is not None and ev.stage == "data_request"


@pytest.mark.asyncio
async def test_remove_required_stage_raises() -> None:
    svc = _svc()
    cert = await svc.create(_OWNER, _CREATE_BUG)
    with pytest.raises(CertificationError, match="requerida"):
        await svc.remove_stage(cert.id, _OWNER, "execution")


@pytest.mark.asyncio
async def test_remove_already_inactive_stage_raises() -> None:
    svc = _svc()
    cert = await svc.create(_OWNER, _CREATE_BUG)
    with pytest.raises(CertificationError):
        await svc.remove_stage(cert.id, _OWNER, "data_request")


# ── update ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_changes_title() -> None:
    svc = _svc()
    cert = await svc.create(_OWNER, _CREATE_BUG)
    cert = await svc.update(cert.id, _OWNER, CertificationUpdate(title="Nuevo"))
    assert cert.title == "Nuevo"


@pytest.mark.asyncio
async def test_update_data_origin_to_factory_activates_stages_for_rest_json() -> None:
    svc = _svc()
    cert = await svc.create(_OWNER, _CREATE_REST)
    assert cert.active_stages["data_request"] == "optional"
    cert = await svc.update(cert.id, _OWNER, CertificationUpdate(data_origin="factory_request"))
    assert cert.active_stages["data_request"] == "required"
    assert cert.active_stages["assignment"] == "required"


# ── source="origin" for auto-activated stages (point 4) ──────────────────────

@pytest.mark.asyncio
async def test_origin_activation_creates_events_with_source_origin() -> None:
    svc = _svc()
    cert = await svc.create(_OWNER, _CREATE_REST)
    cert = await svc.update(cert.id, _OWNER, CertificationUpdate(data_origin="factory_request"))
    origin_events = [e for e in cert.stage_events if e.source == "origin"]
    assert len(origin_events) == 2
    assert {e.stage for e in origin_events} == {"data_request", "assignment"}
    assert all(e.status == "stage_added" for e in origin_events)


@pytest.mark.asyncio
async def test_origin_activation_not_counted_as_analyst_added() -> None:
    svc = _svc()
    cert = await svc.create(_OWNER, _CREATE_REST)
    cert = await svc.update(cert.id, _OWNER, CertificationUpdate(data_origin="factory_request"))
    analyst_events = [e for e in cert.stage_events if e.source == "analyst"]
    assert len(analyst_events) == 0


@pytest.mark.asyncio
async def test_origin_deactivation_creates_source_origin_removed_events() -> None:
    svc = _svc()
    cert = await svc.create(_OWNER, CertificationCreate(
        type="brecha", external_code="B", module="API", title="T",
        recipe_code="service_rest_json", data_origin="factory_request",
    ))
    # data_request and assignment are already required; switching back
    cert = await svc.update(cert.id, _OWNER, CertificationUpdate(data_origin="manual_search"))
    removed = [e for e in cert.stage_events if e.status == "stage_removed" and e.source == "origin"]
    assert len(removed) == 2
    assert {e.stage for e in removed} == {"data_request", "assignment"}


# ── remove_stage additional rejections (point 5) ─────────────────────────────

@pytest.mark.asyncio
async def test_remove_current_stage_raises() -> None:
    svc = _svc()
    cert = await svc.create(_OWNER, _CREATE_REST)
    assert cert.stage == "context"  # current stage
    with pytest.raises(CertificationError, match="en curso"):
        await svc.remove_stage(cert.id, _OWNER, "context")


@pytest.mark.asyncio
async def test_remove_stage_with_data_raises() -> None:
    svc, repo = _svc_with_repo()
    cert = await svc.create(_OWNER, _CREATE_REST)   # data_request is optional
    repo.set_stage_data(cert.id, "data_request", True)
    with pytest.raises(CertificationError, match="datos asociados"):
        await svc.remove_stage(cert.id, _OWNER, "data_request")


@pytest.mark.asyncio
async def test_remove_stage_without_data_succeeds() -> None:
    svc, repo = _svc_with_repo()
    cert = await svc.create(_OWNER, _CREATE_REST)
    repo.set_stage_data(cert.id, "data_request", False)
    cert = await svc.remove_stage(cert.id, _OWNER, "data_request")
    assert cert.active_stages["data_request"] == "not_applicable"


# ── recipe_code is saved correctly for all 8 built-in recipes (RF-01c) ───────

@pytest.mark.asyncio
@pytest.mark.parametrize("recipe_code,cert_type", [
    ("bug_simple", "bug"),
    ("bug_before_after", "bug"),
    ("bug_negative_control", "bug"),
    ("brecha_date_rule", "brecha"),
    ("service_soap_xml", "brecha"),
    ("service_rest_json", "brecha"),
    ("file_batch", "bug"),
    ("client_cases", "bug"),
])
async def test_create_saves_recipe_code_for_all_builtin_recipes(
    recipe_code: str, cert_type: str
) -> None:
    svc = _svc()
    cert = await svc.create(
        _OWNER,
        CertificationCreate(
            type=cert_type,
            external_code=f"TST-{recipe_code[:6]}",
            module="Test",
            title=f"Test {recipe_code}",
            recipe_code=recipe_code,
        ),
    )
    assert cert.recipe_code == recipe_code, (
        f"Esperado recipe_code={recipe_code!r}, obtenido {cert.recipe_code!r}"
    )
    assert cert.active_stages is not None, "active_stages no debe ser None"
