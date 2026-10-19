/**
 * The report in plain words and no values: for each body area, what each result outside its range is, what it
 * does in the body, and which way it is off ("slightly higher than usual"). Built by fixed rules from the analysis
 * (never by a model), so it can't diagnose, reassure or misquote a value. The words live in i18n under "plain"
 * (sentences) and "lay" (what each test is).
 */
import type { Organ, Result } from "../api/types";
import { deviation } from "./format";

export type Tone = "critical" | "out" | "ok" | "info";
export type Direction = "high" | "high_slightly" | "far_high" | "low" | "low_slightly" | "far_low";

/** One result said in plain words: its lay entry and which way it is off (none for an answer in words). */
export interface PlainItem { lay: string; result: Result; direction: Direction | null }

export interface PlainArea { code: string; tone: Tone; items: PlainItem[]; more: boolean }

export interface PlainReport {
  head: "critical" | "all_in" | "mostly_in" | "several_out" | "no_ranges";
  areas: PlainArea[];  // areas with results outside their range, worst first
  fine: string[];  // areas with every result in range
  changed: string[];  // lay entries that changed more than day-to-day variation since last time
  trending: string[];  // lay entries with a confirmed trend
}

const OUT = new Set(["low", "high", "critical_low", "critical_high"]);
const CRITICAL = new Set(["critical_low", "critical_high"]);
const FEW = 0.25;  // above this share of results outside their range, "several" rather than "a few"
const SLIGHTLY = 0.1;  // within a tenth of the bound it crossed: "slightly"
const PER_AREA = 4;

/** Tests that say the same thing to a reader share one entry: the count and the percentage of a cell type. */
const SHARED: Record<string, string> = {
  rdw_sd: "rdw", neut_pct: "neut", neut_abs: "neut", lymph_pct: "lymph", lymph_abs: "lymph", mono_pct: "mono",
  mono_abs: "mono", eos_pct: "eos", eos_abs: "eos", baso_pct: "baso", baso_abs: "baso", ig_pct: "ig", ig_abs: "ig",
  nrbc_pct: "nrbc", nrbc_abs: "nrbc", eag: "hba1c", bun: "urea", bun_creat_ratio: "urea_creat",
  urea_creat_ratio: "urea_creat", hs_crp: "crp", ft4: "t4", ft3: "t3",
};
/** Worked out from other results, or a finer detail of one: named only when nothing more basic in the area is off. */
const SECONDARY = new Set([
  "chol_hdl_ratio", "ldl_hdl_ratio", "hdl_ldl_ratio", "tg_hdl_ratio", "non_hdl", "vldl", "bun_creat_ratio",
  "urea_creat_ratio", "ast_alt_ratio", "ag_ratio", "globulin", "bili_indirect", "mch", "mchc", "rdw", "rdw_sd",
  "mpv", "pdw", "plcr", "pct", "eag",
]);
const SEVERITY: Record<string, number> = { critical_low: 3, critical_high: 3, low: 2, high: 2 };

export function layKey(testCode: string): string {
  return SHARED[testCode] ?? testCode;
}

export function direction(r: Result): Direction | null {
  if (r.answer) return null;
  const high = r.status === "high" || r.status === "critical_high";
  if (CRITICAL.has(r.status)) return high ? "far_high" : "far_low";
  const d = deviation(r);
  const slight = d != null && d.fraction < SLIGHTLY;
  return high ? (slight ? "high_slightly" : "high") : (slight ? "low_slightly" : "low");
}

function area(code: string, results: Result[]): PlainArea | null {
  const out = results.filter((r) => OUT.has(r.status))
    .sort((a, b) => (SEVERITY[b.status] ?? 0) - (SEVERITY[a.status] ?? 0)
      || (deviation(b)?.fraction ?? 0) - (deviation(a)?.fraction ?? 0));
  if (out.length === 0) return null;
  const basic = out.filter((r) => !SECONDARY.has(r.test_code));
  const named = basic.length ? basic : out;
  const items: PlainItem[] = [];
  const seen = new Set<string>();
  for (const r of named) {
    const lay = layKey(r.test_code);
    if (seen.has(lay)) continue;
    seen.add(lay);
    items.push({ lay, result: r, direction: direction(r) });
  }
  return {
    code,
    tone: out.some((r) => CRITICAL.has(r.status)) ? "critical" : "out",
    items: items.slice(0, PER_AREA),
    more: items.length > PER_AREA || named.length < out.length,
  };
}

function uniqueLay(results: Result[], pick: (r: Result) => boolean): string[] {
  return [...new Set(results.filter(pick).map((r) => layKey(r.test_code)))].slice(0, 3);
}

export function plainSummary(organs: Organ[]): PlainReport {
  // results without a range say nothing about where a value sits
  const judged = organs
    .map((o) => ({ code: o.code, results: o.results.filter((r) => r.status !== "unknown") }))
    .filter((o) => o.results.length > 0);
  const results = judged.flatMap((o) => o.results);
  if (results.length === 0) return { head: "no_ranges", areas: [], fine: [], changed: [], trending: [] };

  const outCount = results.filter((r) => OUT.has(r.status)).length;
  const areas = judged.map((o) => area(o.code, o.results)).filter((a): a is PlainArea => a != null)
    .sort((a, b) => Number(b.tone === "critical") - Number(a.tone === "critical"));
  return {
    head: results.some((r) => CRITICAL.has(r.status)) ? "critical"
      : outCount === 0 ? "all_in" : outCount / results.length <= FEW ? "mostly_in" : "several_out",
    areas,
    fine: judged.filter((o) => o.results.every((r) => !OUT.has(r.status))).map((o) => o.code),
    changed: uniqueLay(results, (r) => Boolean(r.change?.significant)),
    trending: uniqueLay(results, (r) => Boolean(r.trend?.confirmed)),
  };
}
