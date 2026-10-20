/**
 * Tipos del API — se derivan de generated.ts (openapi-typescript desde el backend).
 * Ejecutar `npm run check` para regenerar y compilar; una diferencia de forma falla en tsc.
 */
import type { components } from "./generated";

// ── Tipos auxiliares frontend ─────────────────────────────────────────────────

export type CertStage =
  | "context" | "testcases" | "format" | "data_request" | "assignment"
  | "execution" | "analysis" | "documentation" | "review" | "closed";
export type StageMode = "required" | "optional" | "not_applicable";
export type CertType = "bug" | "brecha";
export type CertStatus = "active" | "closed";

export type ActiveStages = Record<CertStage, StageMode>;

// ── Re-exportaciones de los esquemas del backend ──────────────────────────────
// Cuando se ejecuta generate-types el archivo generated.ts se regenera desde el OpenAPI del
// backend y tsc detecta automáticamente cualquier diferencia de forma.

export type Recipe = Omit<components["schemas"]["RecipeRead"], "stages"> & {
  stages: ActiveStages;
};

export type User = components["schemas"]["UserRead"];

export type StageEvent = components["schemas"]["StageEventRead"];

export type Certification = Omit<
  components["schemas"]["CertificationRead"],
  "type" | "stage" | "active_stages" | "stage_events"
> & {
  type: CertType;
  stage: CertStage;
  active_stages: ActiveStages | null;
  stage_events: StageEvent[];
};

export type CompletenessFinding = components["schemas"]["CompletenessFindingOut"];

export type ContextSection = components["schemas"]["SectionOut"];

export type ContextSource = Omit<
  components["schemas"]["ContextSourceOut"],
  "kind" | "sections" | "completeness_findings"
> & {
  kind: "analyst_description" | "requirement_document" | "incident_report" | "analysis_summary";
  sections: ContextSection[] | null;
  completeness_findings: CompletenessFinding[];
};

export type Criterion = components["schemas"]["CriterionOut"];

export type Ambiguity = components["schemas"]["AmbiguityOut"] & { category: string };

export interface TestCaseFlags {
  pending_assumption?: boolean;
  assumption_note?: string | null;
  is_suggestion?: boolean;
  requires_db_verification?: boolean;
  db_verification_note?: string | null;
}

export interface TestCase {
  id: string;
  code: string;
  name: string;
  preconditions: string[];
  steps: string[];
  expected_result: string;
  boundary: string | null;
  status: "draft" | "approved";
  lint_results: Record<string, unknown> | null;
  criteria_ids: string[];
  flags: TestCaseFlags;
  order: number;
}

export interface LintIssue {
  code: string;
  message: string;
  severity: "error" | "warning";
}

export interface TraceabilityRow {
  criterion_id: string;
  criterion_code: string;
  criterion_text: string;
  case_codes: string[];
}

export interface UserBase {
  id: string;
  certification_id: string;
  file_name: string;
  row_count: number;
  header_fingerprint: string;
  mapping_id: string | null;
  columns: string[];
}

export interface UserBasePreview {
  id: string;
  file_name: string;
  row_count: number;
  columns: string[];
  sample: Record<string, string>[];
}

export interface DomainField {
  id: string;
  key: string;
  label: string;
  data_type: string;
  module: string;
  column_name: string | null;
  synonyms: string[];
}

export interface CaseConditions {
  id: string;
  test_case_id: string;
  test_case_code: string;
  test_case_name: string;
  conditions: Record<string, unknown> | null;
  derived_inputs: Array<{ name: string; expr: { base: string; offset: number; unit: string } }>;
  mutates_state: boolean;
  confirmed: boolean;
}

export interface Assignment {
  id: string;
  test_case_id: string;
  test_case_code: string;
  test_case_name: string;
  primary_user: Record<string, string> | null;
  backup_users: Record<string, string>[];
  explanation: string | null;
  missing_data_request: string | null;
  derived_values: Record<string, unknown>;
  manual_override: boolean;
}

export interface DataRequest {
  id: string;
  certification_id: string;
  test_case_id: string;
  text: string;
}

export interface Evidence {
  id: string;
  execution_id: string;
  file_name: string;
  validation_status: "ok" | "warning" | "error" | "pending";
  ocr_time_found: boolean;
  ocr_url_found: boolean;
  caption: string | null;
  accepted_with_reason: string | null;
}

export interface Execution {
  id: string;
  test_case_id: string;
  test_case_code: string;
  test_case_name: string;
  result: "pass" | "fail" | "blocked" | "not_run";
  observation: string | null;
  executed_at: string | null;
}

export interface Deliverable {
  id: string;
  certification_id: string;
  kind: "co_fr_vra_03" | "tfs_note" | "cert_email" | "zip";
  file_name: string;
  file_path: string | null;
  generated_at: string;
}

export interface ReworkEvent {
  id: string;
  certification_id: string;
  test_case_id: string | null;
  reason: string;
  reported_at: string;
}

export interface BaselineCertification {
  id: string;
  owner_id: string;
  type: CertType;
  module: string;
  duration_minutes: number;
  date: string;
  notes: string | null;
}

export interface TaskStatus {
  status: "pending" | "success" | "failure";
  result: Record<string, unknown> | null;
}

export interface MappingSuggestOut {
  suggestions: Record<string, string | null>;
  fingerprint: string;
}

export interface ColumnMappingOut {
  id: string;
  header_fingerprint: string;
  mapping: Record<string, string | null>;
  module: string;
  is_global: boolean;
}
