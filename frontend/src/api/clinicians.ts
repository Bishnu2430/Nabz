import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./client";
import type { Sex, SharedReport } from "./types";

// --- Doctors on Nabz (docs/12 §2) ---------------------------------------------------------------------------------

export interface Registration {
  full_name: string;
  registration_no: string;
  council: string;
  specialty: string | null;
  verified_at: string | null;
}

export interface AdminClinician extends Registration { user_id: string; email: string }

export interface Note { id: string; text: string; created_at: string; clinician_name: string | null }

export interface Grant {
  id: string;
  clinician_name: string;
  registration_no: string;
  council: string;
  specialty: string | null;
  created_at: string;
  revoked: boolean;
  notes: number;
}

export interface SharedWithMe {
  report_id: string;
  person: { display_name: string; sex: Sex; age: number | null };
  lab_name: string | null;
  collected_at: string | null;
  shared_at: string;
  notes: number;
}

export type ClinicianReport = SharedReport & { notes: Note[] };

// the clinician's own side
export const useRegistration = () =>
  useQuery({ queryKey: ["clinician", "me"], queryFn: () => api.get<Registration | null>("/v1/clinician/me") });

export function useSaveRegistration() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Omit<Registration, "verified_at">) => api.put<Registration>("/v1/clinician/me", body),
    onSuccess: (row) => {
      qc.setQueryData(["clinician", "me"], row);
      void qc.invalidateQueries({ queryKey: ["clinician", "shared"] });
    },
  });
}

export const useSharedWithMe = (enabled = true) =>
  useQuery({ queryKey: ["clinician", "shared"], queryFn: () => api.get<SharedWithMe[]>("/v1/clinician/shared"), enabled });

export const useClinicianReport = (id: string) =>
  useQuery({ queryKey: ["clinician", "report", id], queryFn: () => api.get<ClinicianReport>(`/v1/clinician/reports/${id}`), retry: false });

export function useAddNote(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (text: string) => api.post<Note>(`/v1/clinician/reports/${id}/notes`, { text }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["clinician"] }),
  });
}

// the family's side
export const useGrants = (reportId: string) =>
  useQuery({ queryKey: ["grants", reportId], queryFn: () => api.get<Grant[]>(`/v1/reports/${reportId}/grants`) });

export function useGrant(reportId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (email: string) => api.post<Grant>(`/v1/reports/${reportId}/grants`, { email }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["grants", reportId] }),
  });
}

export function useWithdrawGrant(reportId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/v1/grants/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["grants", reportId] }),
  });
}

export const useDoctorNotes = (reportId: string) =>
  useQuery({ queryKey: ["notes", reportId], queryFn: () => api.get<Note[]>(`/v1/reports/${reportId}/notes`) });

// verification: admins
export const useAdminClinicians = () =>
  useQuery({ queryKey: ["admin", "clinicians"], queryFn: () => api.get<AdminClinician[]>("/v1/admin/clinicians") });

export function useVerifyClinician() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, verified }: { id: string; verified: boolean }) =>
      api.post<AdminClinician>(`/v1/admin/clinicians/${id}/verify`, { verified }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "clinicians"] }),
  });
}
