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
