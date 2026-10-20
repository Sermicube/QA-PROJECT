/**
 * Tipos generados automáticamente por openapi-typescript desde el OpenAPI del backend.
 * Ejecutar: npm run generate-types  (requiere backend en localhost:8000)
 * NO EDITAR MANUALMENTE — este archivo es sobreescrito por generate-types.
 *
 * openapi-typescript v7 · Copiloto Certificación QA backend
 */

// Stubs requeridos por openapi-typescript v7
export interface paths {}
export interface webhooks { [key: string]: never }

export interface components {
  schemas: {

    // ── Certifications ────────────────────────────────────────────────────

    StageEventRead: {
      id: string;
      stage: string;
      status?: string | null;
      source?: string | null;
      started_at: string;
      ended_at?: string | null;
    };

    CertificationRead: {
      id: string;
      owner_id: string;
      type: string;
      external_code: string;
      module: string;
      service?: string | null;
      title: string;
      description?: string | null;
      recipe_code?: string | null;
      active_stages?: Record<string, string> | null;
      case_style?: string | null;
      evidence_style?: string | null;
      execution_channel?: string | null;
      data_origin?: string | null;
      stage: string;
      status: string;
      closed_at?: string | null;
      created_at: string;
      updated_at: string;
      stage_events?: components["schemas"]["StageEventRead"][];
      analyst_email?: string | null;
    };

    // ── Recipes ──────────────────────────────────────────────────────────

    RecipeRead: {
      id: string;
      code: string;
      name: string;
      description: string;
      stages: Record<string, string>;
      default_case_style: string;
      default_evidence_style: string;
      default_execution_channel: string;
      default_data_origin: string;
      suggested_case_pattern: string;
      is_builtin: boolean;
      created_at: string;
      updated_at: string;
    };

    // ── Context ───────────────────────────────────────────────────────────

    SectionOut: {
      title: string;
      content: string;
      level: number;
    };

    CompletenessFindingOut: {
      id: string;
      field: string;
      message: string;
      dismissed: boolean;
    };

    ContextSourceOut: {
      id: string;
      certification_id: string;
      kind: string;
      content?: Record<string, unknown> | null;
      file_name?: string | null;
      mime_type?: string | null;
      extracted_text?: string | null;
      sections?: components["schemas"]["SectionOut"][] | null;
      completeness_findings?: components["schemas"]["CompletenessFindingOut"][];
      created_at: string;
      updated_at: string;
    };

    CriterionOut: {
      id: string;
      certification_id: string;
      code: string;
      text: string;
      source_kind: string;
      source_section?: string | null;
      created_at: string;
    };

    AmbiguityOut: {
      id: string;
      certification_id: string;
      type: string;
      fragment: string;
      location: string;
      explanation: string;
      question: string;
      resolution?: string | null;
      resolved_by?: string | null;
      resolved_at?: string | null;
      created_at: string;
    };

    // ── Users ─────────────────────────────────────────────────────────────

    UserRead: {
      id: string;
      email: string;
      full_name: string;
      role: string;
      module?: string | null;
    };

    // ── Tasks (async) ─────────────────────────────────────────────────────

    TaskStatusOut: {
      status: "pending" | "success" | "failure";
      result?: Record<string, unknown> | null;
    };

    AnalyzeOut: {
      task_id: string;
    };

    ProposeDescriptionOut: {
      proposed: Record<string, string>;
    };

  };
  responses: never;
  parameters: never;
  requestBodies: never;
  headers: never;
  pathItems: never;
}

export type $defs = Record<string, never>;
export type operations = Record<string, never>;
