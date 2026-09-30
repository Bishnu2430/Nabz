// Mirrors backend/app/schemas.py. Decimals arrive as strings to keep full precision.

export type ReportStatus =
  | "uploaded" | "rejected" | "queued" | "processing" | "needs_review" | "verified"
  | "analysing" | "explaining" | "explained" | "failed" | "deleted";

export type Sex = "female" | "male" | "other" | "unknown";
export type Lang = "en" | "hi" | "or";
export type Relationship = "self" | "parent" | "child" | "spouse" | "other";

export interface Profile {
  id: string;
  display_name: string;
  sex: Sex;
  date_of_birth: string | null;
  relationship: Relationship;
  preferred_language: Lang;
  reports: number;
  latest_report_at: string | null;
}

export interface ProfileIn {
  display_name: string;
  sex: Sex;
  date_of_birth: string | null;
  relationship: Relationship;
  preferred_language: Lang;
  consent_processing: boolean;
}

export interface Box { page: number; x0: number; top: number; x1: number; bottom: number }

export interface Observation {
  id: string;
  raw_name: string | null;
  raw_value: string | null;
  raw_unit: string | null;
  raw_range: string | null;
  raw_flag: string | null;
  section: string | null;
  test_code: string | null;
  test_name: string | null;
  value: string | null;
  unit: string | null;
  ref_low: string | null;
  ref_high: string | null;
  ref_source: "report" | "catalogue" | "none";
  confidence: number;
  needs_attention: boolean;
  match_method: string | null;
  candidates: [string, string, number][];
  bbox: Box | null;
  edited: boolean;
}

export interface Page { page_no: number; width: number; height: number; source: string; quality: number | null }

export interface Report {
  id: string;
  profile_id: string;
  status: ReportStatus;
  lab_name: string | null;
  collected_at: string | null;
  created_at: string;
  pages: Page[];
  observations: Observation[];
  needs_attention: number;
  unmapped: number;
  confidence_threshold: number;
}

export interface ReportSummary {
  id: string;
  status: ReportStatus;
  lab_name: string | null;
  collected_at: string | null;
  created_at: string;
  rows: number;
}

export interface CatalogueTest { code: string; name: string; short_name: string; panel: string; unit: string; organ: string }

export interface ObservationPatch {
  raw_name?: string;
  raw_value?: string;
  raw_unit?: string;
  raw_range?: string;
  test_code?: string;
}

// --- Analysis (Sprint 4); mirrors the analysis section of backend/app/schemas.py ---------------------------------

export type ObsStatus = "low" | "normal" | "high" | "critical_low" | "critical_high" | "unknown";

export interface Previous { value: number; date: string; report_id: string }

export interface Change {
  fraction: number | null;
  direction: "up" | "down" | "none";
  significant: boolean | null;
  rcv_down: number | null;
  rcv_up: number | null;
}

export interface Projection { kind: "leave" | "enter"; limit: "low" | "high"; value: number; on: string }

export type TrendReason = "" | "too_few" | "short_span" | "not_significant" | "no_variation_data" | "within_variation";

export interface Trend {
  n: number;
  first: string;
  last: string;
  slope_per_year: number;
  intercept: number;
  slope_low: number | null;
  slope_high: number | null;
  p_value: number;
  change_fraction: number | null;
  direction: "rising" | "falling" | "flat";
  confirmed: boolean;
  reason: TrendReason;
  projection: Projection | null;
}

export interface Percentile { value: number; side: "below" | "within" | "above"; population: string; sex: string; age_band: [number, number] }

export interface Result {
  observation_id: string;
  report_id: string;
  date: string;
  test_code: string;
  test_name: string;
  short_name: string;
  organ: string;
  value: string;
  unit: string | null;
  decimals: number;
  ref_low: string | null;
  ref_high: string | null;
  ref_source: string;
  status: ObsStatus;
  critical: boolean;
  flag_disagrees: boolean;
  previous: Previous | null;
  change: Change | null;
  trend: Trend | null;
  percentile: Percentile | null;
}

export interface Organ { code: string; names: Record<string, string>; status: ObsStatus; results: Result[] }

export interface Person { id: string; display_name: string; sex: Sex; age: number | null }

export interface Insights {
  report: ReportSummary;
  person: Person;
  analysed: boolean;
  critical: Result[];
  organs: Organ[];
  explanation: Record<string, unknown> | null;
}

export interface TestInfo {
  code: string;
  name: string;
  short_name: string;
  unit: string;
  decimals: number;
  organ: string;
  rcv_down: number | null;
  rcv_up: number | null;
}

export interface TestHistory { test: TestInfo; person: Person; results: Result[] }

export interface Watch {
  test_code: string;
  test_name: string;
  organ: string;
  n_points: number;
  direction: Trend["direction"] | null;
  confirmed: boolean;
  rcv_significant: boolean | null;
  projected_crossing: string | null;
  percentile: number | null;
  latest: Result;
}

// --- Consent and explanations (Sprint 5) -----------------------------------------------------------------------

export type ConsentPurpose = "processing" | "external_ai" | "voice" | "research";

export interface Consent { purpose: ConsentPurpose; granted: boolean; granted_at: string | null }

export interface TestExplanation {
  test_code: string;
  status: ObsStatus;
  what_it_measures: string;
  what_this_result_means: string;
  citations: string[];
}

export interface Source { label: string; title: string; url: string | null; organisation: string; license: string }

export type TemplateReason = "critical" | "no_consent" | "no_model" | "no_knowledge" | "validation" | "provider_error";

export interface Explanation {
  id: string;
  language: Lang;
  source: "model" | "template";
  reason: TemplateReason | null;
  summary: string;
  per_test: TestExplanation[];
  doctor_questions: string[];
  disclaimer_key: string;
  sources: Source[];
  has_audio: boolean;
  created_at: string;
}

export interface ExplanationState { state: "ready" | "pending" | "none"; explanation: Explanation | null }

// --- Body map (Sprint 6) -------------------------------------------------------------------------------------------

export interface BodyMapOrgan { code: string; status: ObsStatus; out_of_range: number; results: number }

export interface BodyMapFrame { report_id: string; date: string; lab_name: string | null; organs: BodyMapOrgan[] }
