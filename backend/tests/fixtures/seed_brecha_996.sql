-- Seed de demostración: Brecha 996 — getAfiliado / pbs_code para Subsidiado
--
-- Uso: docker exec infra-postgres-1 psql -U copiloto -d copiloto -f /seed_brecha_996.sql
--      (o bien: psql -U copiloto -d copiloto < backend/tests/fixtures/seed_brecha_996.sql)
--
-- Todos los datos son SINTÉTICOS. No contiene cédulas, contratos ni información real.
-- Requiere: alembic upgrade head ejecutado previamente.
-- Es idempotente: se puede ejecutar varias veces sin duplicar filas.

-- ── Usuario demo ─────────────────────────────────────────────────────────────
-- Contraseña: E2eTest1234!  (hash argon2id)
INSERT INTO users (id, email, full_name, password_hash, role, is_active)
VALUES (
    '97470dd7-7157-47bb-b393-ed36c010c21a',
    'e2e@copiloto.local',
    'Analista Demo',
    '$argon2id$v=19$m=65536,t=3,p=4$xNNAdaISLJQULt8WUAj8eQ$BCS8sG2NK3TLcdgDOMinnv4wgZGAJqii4MdJuvYxpOo',
    'analyst',
    true
)
ON CONFLICT (id) DO NOTHING;

-- ── Certificación: Brecha 996 ─────────────────────────────────────────────────
INSERT INTO certifications (
    id, type, recipe_code, external_code, module, title, status,
    case_style, owner_id, active_stages
)
VALUES (
    '99600000-0000-4000-8000-000000000001',
    'brecha',
    'service_rest_json',
    'BRE-996',
    'Afiliados / getAfiliado',
    'Brecha 996 — getAfiliado debe incluir pbs_code para régimen Subsidiado',
    'active',
    'consult_service',
    '97470dd7-7157-47bb-b393-ed36c010c21a',
    '{
        "context":       "required",
        "testcases":     "required",
        "format":        "required",
        "data_request":  "optional",
        "assignment":    "optional",
        "execution":     "required",
        "analysis":      "required",
        "documentation": "required",
        "review":        "required",
        "closed":        "required"
    }'::jsonb
)
ON CONFLICT (id) DO NOTHING;

-- ── Fuente: descripción del analista ─────────────────────────────────────────
INSERT INTO context_sources (id, certification_id, kind, content)
VALUES (
    '99600001-0000-4000-8000-000000000001',
    '99600000-0000-4000-8000-000000000001',
    'analyst_description',
    '{
        "free_text": "Diaz Jimenez, Sergio Alejandro   1 minuto 37 segundos\nVamos a revisar la brecha 996. El servicio getAfiliado debe validar que cuando se\nconsulta un afiliado con régimen Subsidiado la respuesta incluya el campo pbs_code.\n\nRamirez Torres, Claudia   2 minutos 15 segundos\nCorrecto. La validación debe rechazar la solicitud si el campo no viene en la respuesta\ndel WS y retornar el código de error E-200.\n\nDiaz Jimenez, Sergio Alejandro   3 minutos 02 segundos\nEntonces el caso de prueba sería: consultar un titular con régimen S donde pbs_code\nestá ausente y verificar que el servicio retorna E-200.",
        "what_changes": "El servicio getAfiliado ahora incluye el campo pbs_code en la respuesta cuando el afiliado tiene régimen Subsidiado.",
        "what_to_test": "Verificar que el campo pbs_code aparece en la respuesta del servicio para titulares con régimen Subsidiado, y que se retorna E-200 cuando el campo está ausente.",
        "expected_result": "Para régimen Subsidiado: respuesta HTTP 200 con campo pbs_code presente. Para régimen no Subsidiado o sin campo: código de error E-200."
    }'::jsonb
)
ON CONFLICT (id) DO NOTHING;

-- ── Fuente: resumen de análisis (criterios + reglas extraídas) ────────────────
INSERT INTO context_sources (id, certification_id, kind, content)
VALUES (
    '99600002-0000-4000-8000-000000000001',
    '99600000-0000-4000-8000-000000000001',
    'analysis_summary',
    '{
        "business_summary": "La certificación valida que el servicio getAfiliado de Beyond Health incluya el campo pbs_code en la respuesta cuando el afiliado tiene régimen Subsidiado, y que retorne el código de error E-200 cuando el campo está ausente.",
        "rules": [
            "El campo pbs_code debe estar presente en la respuesta del servicio getAfiliado para afiliados con régimen Subsidiado.",
            "Cuando pbs_code está ausente en la respuesta, el servicio debe retornar el código de error E-200.",
            "La validación aplica únicamente a afiliados con régimen Subsidiado; otros regímenes no requieren el campo."
        ]
    }'::jsonb
)
ON CONFLICT (id) DO NOTHING;

-- ── Criterios de aceptación ───────────────────────────────────────────────────
INSERT INTO acceptance_criteria (id, certification_id, code, text, source_kind, source_section)
VALUES
    (
        '99600003-0000-4000-8000-000000000001',
        '99600000-0000-4000-8000-000000000001',
        'CA-01',
        'Para un afiliado con régimen Subsidiado, la respuesta del servicio getAfiliado debe incluir el campo pbs_code.',
        'analyst_description',
        NULL
    ),
    (
        '99600004-0000-4000-8000-000000000001',
        '99600000-0000-4000-8000-000000000001',
        'CA-02',
        'Cuando el campo pbs_code está ausente en la respuesta, el servicio debe retornar el código de error E-200.',
        'analyst_description',
        NULL
    )
ON CONFLICT (id) DO NOTHING;

-- ── Ambigüedades detectadas ───────────────────────────────────────────────────
INSERT INTO ambiguities (id, certification_id, type, fragment, location, explanation, question, category, resolution, resolved_by)
VALUES
    (
        '99600005-0000-4000-8000-000000000001',
        '99600000-0000-4000-8000-000000000001',
        'incomplete_context',
        'El servicio getAfiliado',
        'analyst_description',
        'No se especifica el endpoint ni el método HTTP del servicio.',
        '¿Cuál es el endpoint exacto (URL y método HTTP) del servicio getAfiliado que debe validarse?',
        'execution_data',
        NULL,
        NULL
    ),
    (
        '99600006-0000-4000-8000-000000000001',
        '99600000-0000-4000-8000-000000000001',
        'missing_branch',
        'afiliado con régimen Subsidiado',
        'analyst_description',
        'No está claro si la validación aplica solo a titulares o también a beneficiarios.',
        '¿El campo pbs_code es obligatorio solo para titulares con régimen Subsidiado, o también aplica a beneficiarios?',
        'changes_cases',
        NULL,
        NULL
    ),
    (
        '99600007-0000-4000-8000-000000000001',
        '99600000-0000-4000-8000-000000000001',
        'undefined_result',
        'pbs_code',
        'analyst_description',
        'No se describe el tipo ni el valor esperado del campo pbs_code cuando el afiliado cumple la condición.',
        '¿Qué valor exacto devuelve pbs_code cuando el afiliado cumple la condición (ej. código numérico, booleano o texto)?',
        'changes_cases',
        NULL,
        NULL
    ),
    (
        '99600008-0000-4000-8000-000000000001',
        '99600000-0000-4000-8000-000000000001',
        'incomplete_context',
        'retornar el código de error E-200',
        'analyst_description',
        'No se indica si E-200 va en el cuerpo o en el encabezado HTTP.',
        '¿El código de error E-200 se retorna en el cuerpo de la respuesta o en el encabezado HTTP?',
        'execution_data',
        NULL,
        NULL
    )
ON CONFLICT (id) DO NOTHING;
