import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { Role } from "./auth";
import { api } from "./client";
import type { Lang } from "./types";

// --- The reviewer's console (FR-48) ------------------------------------------------------------------------------

export type ReviewKind = "explanation" | "question" | "feedback";
export interface Span { start: number; end: number; code: string }
export interface Marked { text: string; spans: Span[] }

export interface ReviewItem {
  kind: ReviewKind;
  id: string;
  created_at: string;
  language: Lang;
  age_band: string | null;
  sex: string;
  values: { test: string; value: number; unit: string | null; range_low: number | null; range_high: number | null; status: string }[];
  question: string | null;
  feedback: { helpful: boolean; comment: string | null } | null;
  shown: string;
  blocked: Marked | null;
  problems: { code: string; detail: string }[];
  reason: string | null;
  refusal: string | null;
  mode: string | null;
  review: { verdict: "correct" | "incorrect"; note: string | null; reviewer: string | null; at: string } | null;
}

export interface ReviewSummary {
  explanations: Record<string, number>;
  fallback_reasons: Record<string, number>;
  blocked_rate: number | null;
  questions: Record<string, number>;
  refusals: Record<string, number>;
  feedback: { helpful: number; not_helpful: number };
  open: Record<ReviewKind, number>;
  reviewed: number;
}

export interface CheckResult { text: string; spans: Span[]; problems: { code: string; detail: string }[]; as_question: string | null }

export interface RedteamCase {
  suite: "explanation" | "question";
  id: string;
  language: Lang;
  text: string;
  expect: string;
  category: string;
  found: string[];
  passed: boolean;
}
export interface RedteamRun { totals: Record<"explanation" | "question", { cases: number; passed: number }>; results: RedteamCase[]; ms: number }

export const useReviewSummary = () =>
  useQuery({ queryKey: ["review", "summary"], queryFn: () => api.get<ReviewSummary>("/v1/review/summary") });

export const useReviewQueue = (kind: ReviewKind | "all", state: "open" | "reviewed") =>
  useQuery({
    queryKey: ["review", "queue", kind, state],
    queryFn: () => api.get<ReviewItem[]>(`/v1/review/queue?state=${state}${kind === "all" ? "" : `&kind=${kind}`}`),
  });

export function useVerdict() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ kind, id, verdict, note }: { kind: ReviewKind; id: string; verdict: "correct" | "incorrect"; note?: string }) =>
      api.post(`/v1/review/items/${kind}/${id}`, { verdict, note }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["review"] }),
  });
}

export const useCheck = () =>
  useMutation({ mutationFn: (body: { text: string; language: string }) => api.post<CheckResult>("/v1/review/check", body) });

export const useRedteam = () => useMutation({ mutationFn: () => api.post<RedteamRun>("/v1/review/redteam") });

// --- Running the system (FR-49) -------------------------------------------------------------------------------

export interface Overview {
  health: { database: boolean; worker_last_job: string | null; jobs: Record<string, number>; model: boolean; voice: boolean; embeddings: boolean; mail: string };
  counts: {
    users: Record<string, number>; verified: number; two_step: number; people: number; reports: Record<string, number>;
    records: number; readings: number; reminders: number; share_links: number; explanations: Record<string, number>;
    questions: Record<string, number>; tests: number; passages: number;
  };
  activity: { day: string; uploads: number; explanations: number; questions: number }[];
}

export interface AdminUser {
  id: string;
  email: string;
  role: Role;
  verified: boolean;
  totp: boolean;
  locked: boolean;
  created_at: string;
  last_login_at: string | null;
  sessions: number;
  profiles: number;
}

export interface Job {
  id: number;
  report_id: string;
  stage: string;
  status: string;
  attempts: number;
  error: string | null;
  created_at: string;
  finished_at: string | null;
  locked_by: string | null;
}

export interface AuditEntry {
  id: number;
  at: string;
  actor: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  meta: Record<string, unknown> | null;
}

export const useOverview = () => useQuery({ queryKey: ["admin", "overview"], queryFn: () => api.get<Overview>("/v1/admin/overview") });

export const useAdminUsers = (q: string) =>
  useQuery({ queryKey: ["admin", "users", q], queryFn: () => api.get<AdminUser[]>(`/v1/admin/users${q ? `?q=${encodeURIComponent(q)}` : ""}`) });

export function useUserAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, action, role }: { id: string; action: "role" | "unlock" | "sign-out"; role?: Role }) =>
      action === "role" ? api.patch<AdminUser>(`/v1/admin/users/${id}`, { role }) : api.post<AdminUser>(`/v1/admin/users/${id}/${action}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin"] }),
  });
}

export const useJobs = (state: string) =>
  useQuery({ queryKey: ["admin", "jobs", state], queryFn: () => api.get<Job[]>(`/v1/admin/jobs${state ? `?state=${state}` : ""}`) });

export function useRetryJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.post<Job>(`/v1/admin/jobs/${id}/retry`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin"] }),
  });
}

export const useAudit = (action: string, before?: number) =>
  useQuery({
    queryKey: ["admin", "audit", action, before],
    queryFn: () => api.get<AuditEntry[]>(`/v1/admin/audit?${new URLSearchParams({ ...(action ? { action } : {}), ...(before ? { before: String(before) } : {}) })}`),
  });
