import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./client";
import type { Person, ResultBrief } from "./types";

// --- Reminders -------------------------------------------------------------------------------------------------

export interface Reminder {
  id: string;
  profile_id: string;
  title: string;
  test_code: string | null;
  due_on: string;
  repeat_months: number | null;
  note: string | null;
  sent_at: string | null;
  done_at: string | null;
}

export interface ReminderIn {
  title: string;
  due_on: string;
  test_code?: string;
  repeat_months?: number;
  note?: string;
}

export const useReminders = (profileId: string) =>
  useQuery({ queryKey: ["reminders", profileId], queryFn: () => api.get<Reminder[]>(`/v1/profiles/${profileId}/reminders`) });

function useAfterReminder(profileId: string) {
  const qc = useQueryClient();
  return () => {
    void qc.invalidateQueries({ queryKey: ["reminders", profileId] });
    void qc.invalidateQueries({ queryKey: ["profiles"] });
  };
}

export function useAddReminder(profileId: string) {
  const done = useAfterReminder(profileId);
  return useMutation({
    mutationFn: (body: ReminderIn) => api.post<Reminder>(`/v1/profiles/${profileId}/reminders`, body),
    onSuccess: done,
  });
}

export function useReminderAction(profileId: string) {
  const done = useAfterReminder(profileId);
  return useMutation({
    mutationFn: ({ id, action }: { id: string; action: "done" | "undo" | "send" | "delete" }): Promise<unknown> => {
      if (action === "delete") return api.delete(`/v1/reminders/${id}`);
      if (action === "send") return api.post<Reminder>(`/v1/reminders/${id}/send`);
      return api.patch<Reminder>(`/v1/reminders/${id}`, { done: action === "done" });
    },
    onSuccess: done,
  });
}

export const reminderCalendarUrl = (id: string) => `/v1/reminders/${id}/calendar.ics`;

// --- Home readings ---------------------------------------------------------------------------------------------

export type ReadingKind = "bp" | "glucose" | "weight" | "pulse" | "temperature" | "spo2";
export const READING_KINDS: ReadingKind[] = ["bp", "glucose", "weight", "pulse", "temperature", "spo2"];
export const READING_UNIT: Record<ReadingKind, string> = {
  bp: "mmHg", glucose: "mg/dL", weight: "kg", pulse: "bpm", temperature: "°C", spo2: "%",
};

export interface Reading {
  id: string;
  kind: ReadingKind;
  value: string;
  value2: string | null;
  context: string | null;
  note: string | null;
  taken_at: string;
}

export interface ReadingTarget { low?: string | null; high?: string | null; low2?: string | null; high2?: string | null }

export const useReadings = (profileId: string) =>
  useQuery({ queryKey: ["readings", profileId], queryFn: () => api.get<Reading[]>(`/v1/profiles/${profileId}/readings`) });

export const useReadingTargets = (profileId: string) =>
  useQuery({
    queryKey: ["reading-targets", profileId],
    queryFn: () => api.get<Partial<Record<ReadingKind, ReadingTarget>>>(`/v1/profiles/${profileId}/reading-targets`),
  });

export function useAddReading(profileId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { kind: ReadingKind; value: number; value2?: number; taken_at?: string; context?: string; note?: string }) =>
      api.post<Reading>(`/v1/profiles/${profileId}/readings`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["readings", profileId] }),
  });
}

export function useDeleteReading(profileId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/v1/readings/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["readings", profileId] }),
  });
}

export function useSetReadingTarget(profileId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ kind, target }: { kind: ReadingKind; target: Record<string, number> }) =>
      api.put(`/v1/profiles/${profileId}/reading-targets/${kind}`, target),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["reading-targets", profileId] }),
  });
}

// --- Emergency card --------------------------------------------------------------------------------------------

export interface EmergencyContact { name: string; phone: string; relation?: string | null }

export interface EmergencyInfo {
  blood_group: string | null;
  allergies: string | null;
  conditions: string | null;
  medicines: string | null;
  doctor: string | null;
  contacts: EmergencyContact[];
}

export interface EmergencyCard {
  person: Person;
  info: EmergencyInfo;
  out_of_range: ResultBrief[];
  last_tested: string | null;
  qr_svg: string;
  qr_text: string;
}

export const useEmergencyCard = (profileId: string) =>
  useQuery({ queryKey: ["emergency", profileId], queryFn: () => api.get<EmergencyCard>(`/v1/profiles/${profileId}/emergency`) });

export function useSaveEmergency(profileId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (info: EmergencyInfo) => api.put<EmergencyInfo>(`/v1/profiles/${profileId}/emergency`, info),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["emergency", profileId] }),
  });
}
