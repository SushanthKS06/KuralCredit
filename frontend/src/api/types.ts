export type Role = "applicant" | "reviewer";

export type ApplicationStatus =
  | "created"
  | "consent_pending"
  | "collecting_business_context"
  | "collecting_financial_context"
  | "collecting_issue_details"
  | "collecting_triage_context"
  | "collecting_documents"
  | "resolving_clarifications"
  | "applicant_review"
  | "submitted_for_human_review"
  | "human_review_in_progress"
  | "needs_more_information"
  | "review_completed"
  | "withdrawn"
  | "archived";

export interface SessionOut {
  token: string;
  session_id: string;
  role: Role;
  application_id: string | null;
  display_name: string;
  expires_at: string;
}

export interface SessionInfo {
  session_id: string;
  role: Role;
  application_id: string | null;
  display_name: string;
}

export interface ApplicationCreatePayload {
  applicant_name: string;
  business_name: string;
  language: string;
  voice: string;
  consent_accepted: boolean;
  workflow_id?: string;
  workflow_version?: string;
}

export interface WorkflowSummary {
  id: string;
  name: string;
  domain: string;
  version: string;
  description: string;
  stage_count: number;
  field_count: number;
}

export interface Application {
  id: string;
  reference: string;
  status: ApplicationStatus;
  applicant_name: string;
  business_name: string;
  business_type: string | null;
  workflow_id?: string;
  workflow_version?: string;
  language: string;
  voice: string;
  consent_version: string | null;
  consent_given_at: string | null;
  submitted_at: string | null;
  review_completed_at: string | null;
  created_at: string;
  updated_at: string;
  is_demo: boolean;
  demo_scenario: string | null;
}

export interface CompletenessItem {
  key: string;
  label: string;
  complete: boolean;
  detail: string;
}

export interface Completeness {
  can_submit: boolean;
  missing_fields: string[];
  unconfirmed_fields: string[];
  missing_documents: string[];
  open_clarifications: number;
  items: CompletenessItem[];
}

export interface ApplicationDetail {
  application: Application;
  completeness: Completeness;
}

export interface ApplicationCreated extends ApplicationDetail {
  token: string;
  session_id: string;
  role: "applicant";
  expires_at: string;
}

export interface FinancialFact {
  id: string;
  application_id: string;
  field_key: string;
  label: string;
  raw_value: string;
  normalized_value: string;
  display_value: string;
  currency: string;
  period_start: string | null;
  period_end: string | null;
  period_label: string | null;
  measure_type: string;
  source_type: string;
  source_document_id: string | null;
  source_turn_id: string | null;
  source_locator: string | null;
  provenance_status:
    | "candidate"
    | "applicant_confirmed"
    | "document_extracted"
    | "reviewer_verified"
    | "rejected";
  extraction_method: string;
  model_id: string | null;
  prompt_version: string | null;
  confidence_estimate: number | null;
  version: number;
  supersedes_id: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentRecord {
  id: string;
  application_id: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
  document_type: string;
  parser_profile: string;
  status: string;
  parse_notes: string | null;
  page_count: number | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
}

export interface DocumentUploadResponse {
  document: DocumentRecord;
  facts_created: number;
  extraction_notes: string[];
}

export interface Clarification {
  id: string;
  application_id: string;
  field_key: string;
  question_text: string;
  reason: string;
  expected_answer_type: string;
  status: string;
  priority: number;
  source: string;
  language: string;
  created_at: string;
  answered_at: string | null;
  answer_turn_id: string | null;
}

export interface ConversationTurn {
  id: string;
  application_id: string;
  turn_index: number;
  speaker: string;
  input_mode: string;
  transcript: string;
  language: string;
  intent: string | null;
  target_field: string | null;
  question_id: string | null;
  linked_fact_ids: string[];
  provider_metadata: Record<string, unknown>;
  correction_status: string;
  created_at: string;
}

export interface NextQuestion {
  question_id: string;
  field_key: string;
  prompt: string;
  reason: string;
  expected_answer_type: string;
  source: "workflow" | "clarification";
  clarification_id: string | null;
}

export interface Conversation {
  application_id: string;
  status: ApplicationStatus;
  stage: string;
  turns: ConversationTurn[];
  next_question: NextQuestion | null;
  open_clarifications: Clarification[];
  candidate_facts_count: number;
  note: string | null;
}

export interface TurnResponse {
  turn: ConversationTurn;
  facts_created: number;
  candidate_field_keys: string[];
  extraction_notes: string[];
  next_question: NextQuestion | null;
  conversation: Conversation;
}

export interface TranscribeResponse {
  transcript: string;
  language: string;
  detected_language: string | null;
  provider: string;
  model: string;
  request_id: string | null;
  latency_ms: number;
  note: string | null;
}

export interface SpeechStatus {
  stt_available: boolean;
  tts_available: boolean;
  provider: string;
  supported_audio_formats: string[];
  max_audio_seconds: number;
}

export interface Comparison {
  status: string;
  left_field: string;
  right_field: string;
  left_label: string;
  right_label: string;
  left_value: string | null;
  right_value: string | null;
  difference: string | null;
  percent_difference: string | null;
  tolerance_percent: string | null;
  period_label: string | null;
  explanation: string;
  requires_clarification: boolean;
  clarification_field: string | null;
  clarification_reason: string | null;
  evidence_ids: string[];
}

export interface Reconciliation {
  tolerance_percent: string;
  policy_note: string;
  comparisons: Comparison[];
  status_counts: Record<string, number>;
  missing_required_fields: string[];
  has_blocking_difference: boolean;
  fact_count: number;
  selected_fact_ids: Record<string, string>;
}

export interface AuditEvent {
  id: string;
  application_id: string | null;
  actor: string;
  event_type: string;
  summary: string;
  detail_json: Record<string, unknown>;
  created_at: string;
}

export interface ReviewAction {
  id: string;
  application_id: string;
  reviewer_name: string;
  action: string;
  field_key: string | null;
  reason: string;
  created_at: string;
}

export interface ReviewerSummary {
  source: string;
  prompt_version: string | null;
  applicant_declared_facts: string[];
  document_derived_facts: string[];
  applicant_explanations: string[];
  unresolved_items: string[];
  limitations: string[];
  source_references: string[];
}

export interface ReviewerApplication {
  application: Application;
  completeness: Completeness;
  facts: FinancialFact[];
  documents: DocumentRecord[];
  turns: ConversationTurn[];
  clarifications: Clarification[];
  reconciliation: Reconciliation;
  audit_events: AuditEvent[];
  review_actions: ReviewAction[];
  summary: ReviewerSummary;
  boundary_notice: string;
}

export interface ReviewerQueueItem {
  application_id: string;
  reference: string;
  applicant_name: string;
  business_name: string;
  status: ApplicationStatus;
  submitted_at: string | null;
  created_at: string;
  open_clarifications: number;
  completeness_percent: number;
  is_demo: boolean;
}

export interface ReviewerQueue {
  items: ReviewerQueueItem[];
  total: number;
}

export interface ReviewActionRequest {
  action: "verify_fact" | "reject_fact" | "request_information" | "complete_review";
  field_key?: string;
  reason: string;
}

export interface Voice {
  name: string;
  gender: string;
  model: string;
  languages: string[];
  persona: string | null;
  description: string | null;
}

export interface Language {
  code: string;
  name: string;
  native_name: string;
  script: string;
  stt_supported: boolean;
  voices: Voice[];
}

export interface Capabilities {
  catalog_version: string;
  verified_at: string;
  source_urls: string[];
  stt_max_audio_seconds: number;
  stt_supported_formats: string[];
  stt_max_upload_bytes: number;
  tts_supported_formats: string[];
  languages: Language[];
  defaults: {
    language: string;
    voice: string;
    stt_model: string;
    tts_model: string;
  };
  providers: {
    provider_mode: "real" | "mock";
    mock_mode: boolean;
    live_provider_calls: boolean;
    stt_provider: string;
    tts_provider: string;
    reasoning_provider: string;
    gnani_stt_configured: boolean;
    gnani_tts_configured: boolean;
    groq_configured: boolean;
  };
  features: Record<string, boolean>;
  enabled_workflows?: string[];
}

export interface Health {
  status: string;
  version: string;
  environment: string;
  database: string;
  providers: Record<string, unknown>;
}
