import { describe, expect, it } from "vitest";

import type { Reading } from "../api/care";
import { misses, readingStats, readingText, targetText, within } from "./readings";

const bp = (value: string, value2: string, taken_at: string): Reading =>
  ({ id: taken_at, kind: "bp", value, value2, context: null, note: null, taken_at });

describe("home readings", () => {
  it("writes a reading and its target the way they are said", () => {
    expect(readingText(bp("148.00", "92.00", "2026-09-01T02:00:00Z"))).toBe("148/92");
    expect(readingText({ kind: "weight", value: "78.5", value2: null })).toBe("78.5");
    expect(targetText("bp", { high: "130", high2: "80" })).toBe("< 130/80");
    expect(targetText("glucose", { low: "80", high: "130" })).toBe("80 – 130");
    expect(targetText("spo2", { low: "94" })).toBe("> 94");
    expect(targetText("pulse", {})).toBe("");
  });

  it("says exactly how far each number is from the target", () => {
    const target = { high: "130", high2: "80" };
    expect(misses(bp("148", "92", "x"), target)).toEqual([
      { which: "value", side: "above", by: 18, bound: 130 }, { which: "value2", side: "above", by: 12, bound: 80 }]);
    expect(misses(bp("126", "84", "x"), target)).toEqual([{ which: "value2", side: "above", by: 4, bound: 80 }]);
    expect(misses(bp("124", "78", "x"), target)).toEqual([]);
    expect(misses({ value: "68", value2: null }, { low: "80", high: "130" }))
      .toEqual([{ which: "value", side: "below", by: 12, bound: 80 }]);
    expect(misses(bp("190", "110", "x"), undefined)).toEqual([]);
  });

  it("gives the average, the extremes and how many were outside the target", () => {
    const all = [bp("148", "92", "2026-09-28T02:00:00Z"), bp("126", "78", "2026-09-20T02:00:00Z"),
      bp("134", "88", "2026-06-01T02:00:00Z")];
    const s = readingStats(all, { high: "130", high2: "80" })!;
    expect([s.count, s.mean, s.mean2, s.outside]).toEqual([3, 136, 86, 2]);
    expect([readingText(s.lowest), readingText(s.highest), readingText(s.furthest!)]).toEqual(["126/78", "148/92", "148/92"]);
    expect(readingStats(all, undefined)!.outside).toBeNull();
    expect(readingStats([], undefined)).toBeNull();
    expect(within(all, 30, Date.parse("2026-10-01T00:00:00Z"))).toHaveLength(2);
    expect(within(all, null)).toHaveLength(3);
  });
});
