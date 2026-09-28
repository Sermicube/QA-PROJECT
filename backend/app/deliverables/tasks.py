"""Tarea Celery para generación de entregables (RF-40 a RF-43)."""
from __future__ import annotations

import asyncio
import uuid

from app.core.celery_app import celery_app


@celery_app.task(bind=True, name="deliverables.generate")
def generate_deliverables(self: object, cert_id_str: str, user_id_str: str | None = None) -> dict:
    return asyncio.run(_generate(cert_id_str, user_id_str))


async def _generate(cert_id_str: str, user_id_str: str | None = None) -> dict:
    from pathlib import Path

    from app.certifications.models import Certification
    from app.core.db import async_session_factory
    from app.core.storage import cert_dir
    from app.deliverables.domain.text_templates import render_email, render_tfs_note
    from app.deliverables.domain.zip_builder import build_zip
    from app.deliverables.repository import DeliverableRepository
    from app.evidence.models import Evidence, Execution
    from app.testcases.models import TestCase
    from app.users.models import User
    from sqlalchemy import select

    cert_id = uuid.UUID(cert_id_str)

    async with async_session_factory() as session:
        repo = DeliverableRepository(session)

        # Cargar certificación
        cert_result = await session.execute(select(Certification).where(Certification.id == cert_id))
        cert = cert_result.scalar_one_or_none()
        if cert is None:
            return {"error": "Certificación no encontrada"}

        # Cargar analista
        user_result = await session.execute(select(User).where(User.id == cert.owner_id))
        owner = user_result.scalar_one_or_none()
        analyst_name = owner.full_name if owner else "Analista"

        # Cargar casos con ejecuciones
        cases_result = await session.execute(
            select(TestCase)
            .where(TestCase.certification_id == cert_id, TestCase.status == "approved")
            .order_by(TestCase.order, TestCase.code)
        )
        test_cases = list(cases_result.scalars().all())

        cases_data = []
        for tc in test_cases:
            exec_result = await session.execute(
                select(Execution).where(Execution.test_case_id == tc.id)
            )
            execution = exec_result.scalar_one_or_none()
            cases_data.append({
                "code": tc.code,
                "name": tc.name,
                "steps": tc.steps or [],
                "expected_result": tc.expected_result,
                "result": execution.result if execution else None,
                "observation": execution.observation if execution else None,
            })

        cert_dict = {
            "external_code": cert.external_code,
            "module": cert.module,
            "type": cert.type,
            "title": cert.title,
        }

        output_dir = cert_dir(cert_id)
        generated_files: list[dict] = []

        # ── TFS Note (RF-41) ──────────────────────────────────────────────────
        try:
            tfs_text = render_tfs_note(cert_dict, cases_data)
            tfs_path = output_dir / "tfs_note.txt"
            tfs_path.write_text(tfs_text, encoding="utf-8")
            await repo.upsert(cert_id, "tfs_note", file_path=str(tfs_path), content=tfs_text)
            generated_files.append({"path": str(tfs_path), "arcname": "tfs_note.txt"})
        except Exception as e:
            await repo.upsert(cert_id, "tfs_note", content=f"Error generando nota TFS: {e}")

        # ── Email (RF-42) ─────────────────────────────────────────────────────
        try:
            email_text = render_email(cert_dict, cases_data, analyst_name)
            email_path = output_dir / "email.txt"
            email_path.write_text(email_text, encoding="utf-8")
            await repo.upsert(cert_id, "email", file_path=str(email_path), content=email_text)
            generated_files.append({"path": str(email_path), "arcname": "email.txt"})
        except Exception as e:
            await repo.upsert(cert_id, "email", content=f"Error generando correo: {e}")

        # ── CO-FR-VRA-03 (RF-40) ─────────────────────────────────────────────
        excel_path_str: str | None = None
        try:
            import datetime as _dt
            from app.deliverables.domain.excel_filler import fill_co_fr_vra_03

            # Buscar plantilla: primero en BD, luego en /app/templates/
            template = await repo.get_template("co_fr_vra_03")
            tpl_path: Path | None = None
            if template and Path(template.file_path).exists():
                tpl_path = Path(template.file_path)
            else:
                builtin = Path("/app/templates/CO-FR-VRA-03.xlsx")
                if builtin.exists():
                    tpl_path = builtin

            if tpl_path:
                # Enriquecer casos con datos de evidencia
                for cd in cases_data:
                    tc_obj = next((t for t in test_cases if t.code == cd["code"]), None)
                    if tc_obj:
                        ev_res = await session.execute(
                            select(Evidence).where(
                                Evidence.test_case_id == tc_obj.id,
                                Evidence.ocr_status.in_(["valid", "warning"]),
                            )
                        )
                        ev_list = list(ev_res.scalars().all())
                        if ev_list:
                            cd["evidence_description"] = ev_list[0].description or ""

                today = _dt.date.today()
                excel_out = output_dir / f"CO-FR-VRA-03_{cert.external_code}.xlsx"
                fill_co_fr_vra_03(
                    template_path=tpl_path,
                    output_path=excel_out,
                    title=cert.title,
                    external_code=cert.external_code,
                    module=cert.module,
                    cert_type=cert.type,
                    description=cert.description or "",
                    analyst_name=analyst_name,
                    start_date=today,
                    end_date=today,
                    test_cases=cases_data,
                )
                excel_path_str = str(excel_out)
                await repo.upsert(cert_id, "co_fr_vra_03", file_path=excel_path_str)
                generated_files.append({"path": excel_path_str, "arcname": excel_out.name})
        except Exception as _exc:
            import logging
            logging.getLogger(__name__).warning("CO-FR-VRA-03 generation failed: %s", _exc)

        # ── Evidencias válidas ────────────────────────────────────────────────
        for tc in test_cases:
            ev_result = await session.execute(
                select(Evidence).where(
                    Evidence.test_case_id == tc.id,
                    Evidence.ocr_status.in_(["valid", "warning"]),
                )
            )
            for ev in ev_result.scalars().all():
                generated_files.append({
                    "path": ev.file_path,
                    "arcname": f"evidencias/{tc.code}_{ev.file_name}",
                })

        # ── ZIP (RF-43) ───────────────────────────────────────────────────────
        try:
            zip_bytes = build_zip(cert_id_str, generated_files)
            zip_path = output_dir / f"certificacion_{cert.external_code}.zip"
            zip_path.write_bytes(zip_bytes)
            await repo.upsert(cert_id, "zip", file_path=str(zip_path))
        except Exception as e:
            pass

        await session.commit()
        return {"generated": [f["arcname"] for f in generated_files]}
