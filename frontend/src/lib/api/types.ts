export type CertStage = "context" | "ambiguities" | "testcases" | "testdata" | "execution" | "deliverables" | "closed";
export type CertType = "bug" | "brecha";
export type CertStatus = "active" | "closed";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  module?: string;
}

export interface Certification {
  id: string;
  owner_id: string;
  type: CertType;
  external_code: string;
  module: string;
  title: string;
  description: string | null;
  stage: CertStage;
  status: string;
  closed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ContextSource {
  id: string;
  certification_id: string;
  kind: "analyst_description" | "requirement_document" | "incident_report";
  content: Record<string, unknown> | null;
  extracted_text: string | null;
  sections: Array<{ title: string; content: string }> | null;
  file_name: string | null;
}

export interface Criterion {
  id: string;
  code: string;
  text: string;
  source_kind: string;
}

export interface Ambiguity {
  id: string;
  type: string;
  fragment: string;
  location: string;
  explanation: string;
  question: string;
  resolution: string | null;
  resolved_by: string | null;
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
