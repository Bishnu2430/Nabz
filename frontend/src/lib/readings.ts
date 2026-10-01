/** Home readings against the person's own target: exact distances, never a judgement. */

import type { Reading, ReadingKind, ReadingTarget } from "../api/care";

const DECIMALS: Record<ReadingKind, number> = { bp: 0, glucose: 0, weight: 1, pulse: 0, temperature: 1, spo2: 0 };

export const readingDecimals = (kind: ReadingKind) => DECIMALS[kind];

const num = (v: number, kind: ReadingKind) => v.toFixed(DECIMALS[kind]);

/** "148/92", "132", "78.5": the reading as it is said, without its unit. */
export function readingText(r: Pick<Reading, "kind" | "value" | "value2">): string {
  const first = num(Number(r.value), r.kind);
  return r.kind === "bp" && r.value2 != null ? `${first}/${num(Number(r.value2), r.kind)}` : first;
}

/** "< 130/80", "80 – 130", "> 94": the target as the person entered it; "" when there is none. */
export function targetText(kind: ReadingKind, target: ReadingTarget | undefined): string {
  if (!target) return "";
  const n = (v: string | null | undefined) => (v == null ? null : num(Number(v), kind));
  const [lo, hi, hi2] = [n(target.low), n(target.high), n(target.high2)];
  if (kind === "bp") {
    if (hi && hi2) return `< ${hi}/${hi2}`;
    if (hi) return `< ${hi}`;
    if (hi2) return `< –/${hi2}`;
    return "";
  }
  if (lo && hi) return `${lo} – ${hi}`;
  if (hi) return `< ${hi}`;
  if (lo) return `> ${lo}`;
  return "";
}

export interface Miss {
  /** Which number of the reading: the first (or only) one, or blood pressure's lower number. */
  which: "value" | "value2";
  side: "above" | "below";
  by: number;
  bound: number;
}

/** Where a reading falls outside the target, one entry per number that does; empty when inside or no target. */
export function misses(r: Pick<Reading, "value" | "value2">, target: ReadingTarget | undefined): Miss[] {
  if (!target) return [];
  const out: Miss[] = [];
  const check = (which: Miss["which"], raw: string | null, low?: string | null, high?: string | null) => {
    if (raw == null) return;
    const v = Number(raw);
    if (high != null && v > Number(high)) out.push({ which, side: "above", by: v - Number(high), bound: Number(high) });
    else if (low != null && v < Number(low)) out.push({ which, side: "below", by: Number(low) - v, bound: Number(low) });
  };
  check("value", r.value, target.low, target.high);
  check("value2", r.value2, target.low2, target.high2);
  return out;
}

export interface ReadingStats {
  count: number;
  mean: number;
  mean2: number | null;
  lowest: Reading;
  highest: Reading;
  /** Readings with a number outside the target; null when there is no target. */
  outside: number | null;
  /** The reading furthest outside the target, by its worst number. */
  furthest: Reading | null;
}

/** The average, the lowest and the highest of a set of readings of one kind (by the first number). */
export function readingStats(readings: Reading[], target: ReadingTarget | undefined): ReadingStats | null {
  if (readings.length === 0) return null;
  const mean = (xs: number[]) => xs.reduce((a, b) => a + b, 0) / xs.length;
  const seconds = readings.filter((r) => r.value2 != null).map((r) => Number(r.value2));
  const by = [...readings].sort((a, b) => Number(a.value) - Number(b.value));
  const hasTarget = Boolean(target && Object.values(target).some((v) => v != null));
  const worst = (r: Reading) => Math.max(0, ...misses(r, target).map((m) => m.by));
  const out = readings.filter((r) => worst(r) > 0).sort((a, b) => worst(b) - worst(a));
  return {
    count: readings.length,
    mean: mean(readings.map((r) => Number(r.value))),
    mean2: seconds.length ? mean(seconds) : null,
    lowest: by[0],
    highest: by[by.length - 1],
    outside: hasTarget ? out.length : null,
    furthest: out[0] ?? null,
  };
}

/** Readings taken on or after `days` before `now`; every reading when `days` is null. */
export function within(readings: Reading[], days: number | null, now = Date.now()): Reading[] {
  if (days == null) return readings;
  const from = now - days * 86_400_000;
  return readings.filter((r) => Date.parse(r.taken_at) >= from);
}

export const formatReadingNumber = num;
