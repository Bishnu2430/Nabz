import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api } from "./client";
import type {
  BodyMapFrame, CatalogueTest, HealthRecord, OrganHistory, RecordKind, Consent, ConsentPurpose, ExplanationState, Insights, Observation, ObservationPatch, Profile, ProfileIn,
  Report, ReportStatus, ReportSummary,
  TestHistory, Watch,
} from "./types";

export const useProfiles = () => useQuery({ queryKey: ["profiles"], queryFn: () => api.get<Profile[]>("/v1/profiles") });

export const useReports = (profileId: string) =>
  useQuery({
    queryKey: ["reports", profileId],
    queryFn: () => api.get<ReportSummary[]>(`/v1/profiles/${profileId}/reports`),
  });

/** Polls slowly while the report is processing, as a safety net under the SSE stream. */
export const useReport = (reportId: string, enabled = true) =>
  useQuery({
    queryKey: ["report", reportId],
    enabled: enabled && Boolean(reportId),
    queryFn: () => api.get<Report>(`/v1/reports/${reportId}`),
    refetchInterval: (q) => (q.state.data && IN_PROGRESS.has(q.state.data.status) ? 4000 : false),
  });

export const useCatalogue = () =>
  useQuery({
    queryKey: ["catalogue"],
    queryFn: () => api.get<CatalogueTest[]>("/v1/catalogue/tests"),
    staleTime: Infinity,
  });

export function useCreateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ProfileIn) => api.post<Profile>("/v1/profiles", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["profiles"] }),
  });
}

/** Hard delete (FR-33): the person, every report and file, and everything derived from them. */
export function useDeleteProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (profileId: string) => api.delete(`/v1/profiles/${profileId}`),
    onSuccess: (_, profileId) => {
      qc.removeQueries({ queryKey: ["reports", profileId] });
      return qc.invalidateQueries({ queryKey: ["profiles"] });
    },
  });
}

export function useUpload(profileId: string) {
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return api.post<{ report_id: string; status: ReportStatus }>(`/v1/profiles/${profileId}/reports`, form);
    },
  });
}

export const IN_PROGRESS: ReadonlySet<ReportStatus> = new Set(["uploaded", "queued", "processing"]);

/**
 * Live report status via Server-Sent Events. Each change also refreshes the cached report.
 * The server ends the stream once processing stops; the browser's automatic reconnect is suppressed.
 */
export function useReportStatus(reportId: string | undefined): ReportStatus | undefined {
  const qc = useQueryClient();
  const [status, setStatus] = useState<ReportStatus>();
  useEffect(() => {
    if (!reportId || typeof EventSource === "undefined") return;
    const source = new EventSource(`/v1/reports/${reportId}/events`);
    source.addEventListener("status", (e) => {
      const next = JSON.parse((e as MessageEvent).data).status as ReportStatus;
      setStatus(next);
      void qc.invalidateQueries({ queryKey: ["report", reportId] });
      void qc.invalidateQueries({ queryKey: ["reports"] });
    });
    source.onerror = () => source.close();
    return () => source.close();
  }, [reportId, qc]);
  return status;
}

function useReportMutation<TArgs, TResult>(reportId: string, fn: (args: TArgs) => Promise<TResult>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () =>
      Promise.all([
        qc.invalidateQueries({ queryKey: ["report", reportId] }),
        qc.invalidateQueries({ queryKey: ["reports"] }),
      ]),
  });
}

export const useEditObservation = (reportId: string) =>
  useReportMutation(reportId, ({ id, patch }: { id: string; patch: ObservationPatch }) =>
    api.patch<Observation>(`/v1/observations/${id}`, patch));

export const useAddObservation = (reportId: string) =>
  useReportMutation(reportId, (body: { test_code: string; raw_value: string; raw_unit?: string; raw_range?: string }) =>
    api.post<Observation>(`/v1/reports/${reportId}/observations`, body));

export const useDeleteObservation = (reportId: string) =>
  useReportMutation(reportId, (id: string) => api.delete(`/v1/observations/${id}`));

export const useConfirm = (reportId: string) =>
  useReportMutation(reportId, (collected_at: string | null) =>
    api.post<{ report_id: string; status: ReportStatus }>(`/v1/reports/${reportId}/confirm`,
      collected_at ? { collected_at } : {}));

// --- Analysis -------------------------------------------------------------------------------------------------

const ANALYSING: ReadonlySet<ReportStatus> = new Set(["verified", "analysing"]);

/** Polls while the analysis stage hasn't run yet. */
export const useInsights = (reportId: string) =>
  useQuery({
    queryKey: ["insights", reportId],
    queryFn: () => api.get<Insights>(`/v1/reports/${reportId}/insights`),
    refetchInterval: (q) => (q.state.data && !q.state.data.analysed && ANALYSING.has(q.state.data.report.status) ? 2000 : false),
  });

export const useTestHistory = (profileId: string, code: string) =>
  useQuery({
    queryKey: ["history", profileId, code],
    queryFn: () => api.get<TestHistory>(`/v1/profiles/${profileId}/tests/${code}`),
  });

export const useWatch = (profileId: string) =>
  useQuery({ queryKey: ["watch", profileId], queryFn: () => api.get<Watch[]>(`/v1/profiles/${profileId}/watch`) });

// --- Consent and explanations ----------------------------------------------------------------------------------

export const useConsents = (profileId: string) =>
  useQuery({ queryKey: ["consents", profileId], queryFn: () => api.get<Consent[]>(`/v1/profiles/${profileId}/consents`) });

export function useSetConsent(profileId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ purpose, granted }: { purpose: ConsentPurpose; granted: boolean }) =>
      api.put<Consent>(`/v1/profiles/${profileId}/consents/${purpose}`, { granted }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["consents", profileId] }),
  });
}

/** Polls while the explanation is being written. */
export const useExplanation = (reportId: string, lang: string) =>
  useQuery({
    queryKey: ["explanation", reportId, lang],
    queryFn: () => api.get<ExplanationState>(`/v1/reports/${reportId}/explanation?lang=${lang}`),
    refetchInterval: (q) => (q.state.data?.state === "pending" ? 3000 : false),
  });

export function useRequestExplanation(reportId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ language, regenerate = false }: { language: string; regenerate?: boolean }) =>
      api.post<ExplanationState>(`/v1/reports/${reportId}/explanation`, { language, regenerate }),
    onSuccess: (_, v) => qc.invalidateQueries({ queryKey: ["explanation", reportId, v.language] }),
  });
}

export const useNarrate = () =>
  useMutation({ mutationFn: (explanationId: string) => api.post<{ url: string }>(`/v1/explanations/${explanationId}/audio`) });

export const useFeedback = () =>
  useMutation({
    mutationFn: ({ id, helpful }: { id: string; helpful: boolean }) =>
      api.post(`/v1/explanations/${id}/feedback`, { helpful }),
  });

export const useBodyMap = (profileId: string) =>
  useQuery({
    queryKey: ["body-map", profileId],
    queryFn: () => api.get<BodyMapFrame[]>(`/v1/profiles/${profileId}/body-map`),
  });

/** Every test of one organ system with its whole history (the body map's organ panel). */
export const useOrganHistory = (profileId: string, organ: string | null) =>
  useQuery({
    queryKey: ["organ", profileId, organ],
    enabled: Boolean(profileId && organ),
    queryFn: () => api.get<OrganHistory>(`/v1/profiles/${profileId}/organs/${organ}`),
  });

export function useReportNote(reportId: string, profileId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (note: string) => api.patch<ReportSummary>(`/v1/reports/${reportId}`, { note }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["reports", profileId] });
      void qc.invalidateQueries({ queryKey: ["insights", reportId] });
    },
  });
}

// --- Other health records ----------------------------------------------------------------------------------------

export const useRecords = (profileId: string) =>
  useQuery({
    queryKey: ["records", profileId],
    queryFn: () => api.get<HealthRecord[]>(`/v1/profiles/${profileId}/records`),
  });

export interface RecordIn {
  file: File;
  kind: RecordKind;
  title: string;
  record_date?: string;
  facility?: string;
  notes?: string;
}

export function useAddRecord(profileId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (r: RecordIn) => {
      const form = new FormData();
      form.append("file", r.file);
      form.append("kind", r.kind);
      form.append("title", r.title);
      if (r.record_date) form.append("record_date", r.record_date);
      if (r.facility) form.append("facility", r.facility);
      if (r.notes) form.append("notes", r.notes);
      return api.post<HealthRecord>(`/v1/profiles/${profileId}/records`, form);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["records", profileId] }),
  });
}

export function useDeleteRecord(profileId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/v1/records/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["records", profileId] }),
  });
}

export const recordFileUrl = (id: string) => `/v1/records/${id}/file`;
export const recordImageUrl = (id: string) => `/v1/records/${id}/image`;
