import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api } from "./client";
import type {
  CatalogueTest, Observation, ObservationPatch, Profile, ProfileIn, Report, ReportStatus, ReportSummary,
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
