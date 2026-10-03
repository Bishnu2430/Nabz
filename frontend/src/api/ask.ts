import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./client";
import type { Lang, Source } from "./types";

export type AnswerMode = "model" | "knowledge" | "refusal";
export type Refusal = "instruction" | "emergency" | "treatment" | "diagnosis" | "not_in_report" | "off_topic" | "cannot_answer";

/** A question about a report and what Nabz said (FR-47). */
export interface Question {
  id: string;
  language: Lang;
  question: string;
  answer: string;
  mode: AnswerMode;
  refusal: Refusal | null;
  /** Why rules wrote the answer instead of the AI service. */
  reason: "critical" | "no_consent" | "no_model" | "no_knowledge" | "validation" | "provider_error" | null;
  test_codes: string[];
  sources: Source[];
  created_at: string;
}

export const useQuestions = (reportId: string) =>
  useQuery({ queryKey: ["questions", reportId], queryFn: () => api.get<Question[]>(`/v1/reports/${reportId}/questions`) });

export function useAsk(reportId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { question: string; language: string }) => api.post<Question>(`/v1/reports/${reportId}/ask`, body),
    onSuccess: (made) => qc.setQueryData<Question[]>(["questions", reportId], (old) => [...(old ?? []), made]),
  });
}

export function useDeleteQuestion(reportId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/v1/questions/${id}`),
    onSuccess: (_, id) => qc.setQueryData<Question[]>(["questions", reportId], (old) => (old ?? []).filter((q) => q.id !== id)),
  });
}
