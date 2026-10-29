export type UserRole = "institution" | "official" | "admin" | "auditor";

export interface User {
  id: number;
  email: string;
  role: UserRole;
  full_name: string;
  institution_id?: number | null;
  is_active: boolean;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
  role: UserRole;
  user_id: number;
  full_name: string;
  institution_id?: number | null;
}

export interface Institution {
  id: number;
  name: string;
  trust_name: string;
  address: string;
  state: string;
  aicte_id: string;
}

export interface ChecklistItem {
  id: number;
  application_type: string;
  doc_type: string;
  mandatory: number;
  validity_required: number;
  description: string;
}

export interface ExtractedField {
  id: number;
  document_id: number;
  key: string;
  value: string | null;
  ocr_confidence: number;
  extraction_method: string;
  page: number;
  bbox: { x?: number; y?: number; width?: number; height?: number } | Record<string, any>;
  needs_review: boolean;
  edited_by?: number | null;
  edited_value?: string | null;
}

export interface DocumentItem {
  id: number;
  application_id: number;
  doc_type: string;
  original_filename: string;
  stored_path: string;
  mime_type: string;
  size: number;
  sha256?: string | null;
  phash?: string | null;
  page_count: number;
  processing_status: "queued" | "processing" | "completed" | "failed";
  processing_stage: string;
  processing_error?: string | null;
  validation_status: "valid" | "incomplete" | "expired" | "mismatch" | "missing" | "unable_to_verify" | "pending_processing";
  official_verification_status?: "pending_review" | "verified" | "rejected" | "requires_correction" | "mismatch_confirmed" | "unable_to_verify" | string | null;
  official_remarks?: string | null;
  verified_at?: string | null;
  verified_by?: number | null;
  uploaded_at: string;
  superseded_by?: number | null;
  extracted_fields: ExtractedField[];
}

export interface FlagItem {
  id: number;
  application_id: number;
  document_id?: number | null;
  related_document_id?: number | null;
  category: "missing" | "expired" | "incomplete" | "mismatch" | "duplicate" | "tampering" | "metadata" | "verification" | "compliance" | "quality";
  severity: "critical" | "warning" | "info";
  title: string;
  explanation: string;
  evidence: Record<string, any>;
  bbox?: Record<string, any> | null;
  confidence: number;
  confidence_meaning: string;
  rule_ref?: string | null;
  status: "open" | "acknowledged" | "dismissed";
  dismissed_reason?: string | null;
  created_at: string;
}

export interface VerificationResultItem {
  id: number;
  document_id: number;
  authority: string;
  adapter_name: string;
  reference_no?: string | null;
  ocr_reference_no?: string | null;
  manual_reference_no?: string | null;
  verification_mode?: string | null;
  manual_remarks?: string | null;
  status: "verified" | "in_progress" | "not_verified" | "pending" | "unable_to_verify";
  is_simulated: boolean;
  raw_response: Record<string, any>;
  message?: string | null;
  checked_at: string;
}

export interface ComplianceRuleItem {
  id: number;
  rule_key: string;
  name: string;
  clause: string;
  source: string;
  program: string;
  parameters: Record<string, any>;
  check_type: string;
  version: number;
  active: boolean;
  verified_against_handbook: boolean;
  on_missing_data: string;
}

export interface ComplianceResultItem {
  id: number;
  application_id: number;
  rule_id: number;
  rule_version: number;
  required_value: string;
  provided_value?: string | null;
  outcome: "compliant" | "needs_review" | "needs_update" | "non_compliant";
  explanation: string;
  rule?: ComplianceRuleItem;
}

export interface ApplicationItem {
  id: number;
  application_no: string;
  institution_id: number;
  type: string;
  academic_year: string;
  status: "draft" | "submitted" | "processing" | "under_verification" | "needs_review" | "info_requested" | "approved" | "rejected";
  risk_score: number;
  risk_band: "Low" | "Medium" | "High";
  risk_breakdown: Record<string, any>;
  declared_details: Record<string, any>;
  created_at: string;
  submitted_at?: string | null;
  institution?: Institution;
}

export interface DashboardSummary {
  total_applications: number;
  draft?: number;
  submitted?: number;
  under_verification: number;
  needs_review: number;
  approved: number;
  rejected: number;
  info_requested: number;
  status_distribution: { status: string; count: number; percentage?: number }[];
  recent_alerts: {
    id: number;
    application_id: number;
    application_no: string;
    institution_name: string;
    title: string;
    severity: string;
    category: string;
    finding_group?: string;
    affected_document?: string;
    review_status?: string;
    created_at: string;
  }[];
  high_risk_applications: {
    id: number;
    application_no: string;
    institution_name: string;
    state: string;
    risk_score: number;
    risk_band: string;
    status: string;
    critical_flags_count: number;
    unresolved_flags_count?: number;
    reasons?: string[];
    submission_date?: string | null;
  }[];
  processing_stats: {
    avg_processing_time_sec: number;
    total_processed_documents: number;
    ocr_success_rate: number;
    native_pdf_count?: number;
    ocr_count?: number;
    pending_jobs?: number;
    failed_jobs?: number;
    reporting_period?: string;
    last_refresh_time?: string;
  };
}

export interface NotificationItem {
  id: number;
  user_id?: number | null;
  target_role?: string | null;
  institution_id?: number | null;
  category: string;
  title: string;
  message: string;
  link?: string | null;
  application_id?: number | null;
  is_read: boolean;
  created_at: string;
  read_at?: string | null;
}

export interface DeficiencyRequirement {
  id: string;
  doc_type: string;
  requirement: string;
  explanation: string;
  mandatory: boolean;
}

export interface InformationRequestItem {
  id: number;
  reference_no: string;
  application_id: number;
  application_no?: string;
  institution_id: number;
  institution_name?: string;
  title: string;
  reason: string;
  notice_text?: string | null;
  deficiencies: DeficiencyRequirement[];
  status: "draft" | "action_required" | "submitted" | "under_review" | "further_info_required" | "resolved";
  issued_by_id?: number | null;
  issued_by_name?: string | null;
  issued_at?: string | null;
  deadline?: string | null;
  resolved_at?: string | null;
  resolution_notes?: string | null;
  created_at: string;
}

export interface ResponseItem {
  deficiency_id: string;
  explanation: string;
  document_id?: number | null;
  original_filename?: string | null;
  status: string;
}

export interface InformationResponseItem {
  id: number;
  request_id: number;
  submitted_by_id: number;
  submitted_by_name?: string;
  items: ResponseItem[];
  status: "draft" | "submitted" | "under_review" | "accepted" | "revision_requested";
  version?: number;
  receipt_no?: string | null;
  submitted_at?: string | null;
  review_remarks?: string | null;
  created_at: string;
  updated_at: string;
}

