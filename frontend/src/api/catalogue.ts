import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./client";
import type { Sex } from "./types";

// --- The catalogue and the knowledge base on the console (FR-35, FR-36) --------------------------------------------
// Numbers arrive as strings (exact decimals) and are sent back as typed.

export interface Conversion { from_unit: string; factor: string; offset: string }
export interface RangeRow { sex: Sex; age_min: number; age_max: number; low: string | null; high: string | null }

export interface CriticalLimit {
  low: string | null;
  high: string | null;
  source: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  proposed: { low: string | null; high: string | null; at: string; by: string | null; note: string | null } | null;
}

export interface CatalogueRow {
  code: string;
  name: string;
  short_name: string;
  organ: string;
  unit: string;
  aliases: number;
  conversions: number;
  ranges: number;
  critical: CriticalLimit | null;
}

export interface CatalogueChange { at: string; actor: string | null; action: string; meta: Record<string, unknown> | null }

export interface CatalogueTest {
  code: string;
  loinc: string;
  name: string;
  short_name: string;
  panel: string;
  organ: string;
  unit: string;
  decimals: number;
  plausible_min: string;
  plausible_max: string;
  aliases: string[];
  conversions: Conversion[];
  ranges: RangeRow[];
  critical: CriticalLimit | null;
  history: CatalogueChange[];
}

export interface TestPatch {
  name?: string;
  short_name?: string;
  aliases?: string[];
  decimals?: number;
  plausible_min?: string;
  plausible_max?: string;
}

export interface LimitForReview { code: string; name: string; unit: string; critical: CriticalLimit; ranges: RangeRow[] }

export interface KbDocument {
  id: string;
  title: string;
  source_org: string;
  url: string | null;
  license: string;
  language: string;
  retrieved_at: string | null;
  chunks: number;
  tests: string[];
  citations: number;
}

export interface KbDocumentIn {
  title: string;
  source_org: string;
  url: string;
  license: string;
  language: string;
  retrieved_at?: string;
  test_code: string;
  text: string;
}

export const useAdminCatalogue = (q: string) =>
  useQuery({ queryKey: ["admin", "catalogue", q], queryFn: () => api.get<CatalogueRow[]>(`/v1/admin/catalogue${q ? `?q=${encodeURIComponent(q)}` : ""}`) });

export const useCatalogueTest = (code: string) =>
  useQuery({ queryKey: ["admin", "catalogue-test", code], queryFn: () => api.get<CatalogueTest>(`/v1/admin/catalogue/${code}`) });

/** Every edit returns the test as it now is; the list is refreshed behind it. */
export function useEditCatalogue(code: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (change: { kind: "test"; body: TestPatch } | { kind: "conversions"; body: Conversion[] }
      | { kind: "ranges"; body: RangeRow[] } | { kind: "limit"; body: { low: string | null; high: string | null; note: string } }) => {
      const base = `/v1/admin/catalogue/${code}`;
      if (change.kind === "test") return api.patch<CatalogueTest>(base, change.body);
      if (change.kind === "conversions") return api.put<CatalogueTest>(`${base}/conversions`, change.body);
      if (change.kind === "ranges") return api.put<CatalogueTest>(`${base}/ranges`, change.body);
      return api.put<CatalogueTest>(`${base}/critical-limit`, change.body);
    },
    onSuccess: (test) => {
      qc.setQueryData(["admin", "catalogue-test", code], test);
      void qc.invalidateQueries({ queryKey: ["admin", "catalogue"] });
    },
  });
}

export const useLimitsForReview = () =>
  useQuery({ queryKey: ["review", "limits"], queryFn: () => api.get<LimitForReview[]>("/v1/review/critical-limits") });

export function useDecideLimit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ code, approve, note }: { code: string; approve: boolean; note?: string }) =>
      api.post<{ critical: CriticalLimit | null; results_changed: number }>(`/v1/review/critical-limits/${code}`, { approve, note: note || undefined }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["review", "limits"] }),
  });
}

export const useKnowledge = () =>
  useQuery({ queryKey: ["admin", "knowledge"], queryFn: () => api.get<{ documents: KbDocument[]; chunks: number; embedder: string | null }>("/v1/admin/knowledge") });

export function useKnowledgeAction() {
  const qc = useQueryClient();
  return useMutation({
    /** Adding and re-embedding report how many passages they embedded; deleting returns nothing. */
    mutationFn: async (action: { kind: "add"; body: KbDocumentIn } | { kind: "reembed"; id?: string } | { kind: "delete"; id: string })
      : Promise<{ chunks: number; ms?: number } | undefined> => {
      if (action.kind === "add") return api.post<KbDocument>("/v1/admin/knowledge", action.body);
      if (action.kind === "reembed") {
        return api.post<{ documents: number; chunks: number; ms: number }>(`/v1/admin/knowledge${action.id ? `/${action.id}` : ""}/reembed`);
      }
      await api.delete(`/v1/admin/knowledge/${action.id}`);
      return undefined;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "knowledge"] }),
  });
}
