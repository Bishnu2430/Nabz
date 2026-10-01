import { describe, expect, it } from "vitest";

import type { BodyMapFrame, HealthRecord, ReportSummary, ResultBrief } from "../api/types";
import { buildStory, chapterMs } from "./story";

const r = (over: Partial<ResultBrief>): ResultBrief => ({
  test_code: "hba1c", test_name: "HbA1c", short_name: "HbA1c", value: "5.4", unit: "%", decimals: 1, status: "normal",
  ref_low: "4.0", ref_high: "5.6", date: "2021-03-18", report_id: "r1", ...over });
const frame = (id: string, date: string, tests: ResultBrief[]): BodyMapFrame => ({
  report_id: id, date, lab_name: "Lab", organs: [{ code: "pancreas", status: "normal", out_of_range: 0, results: tests.length,
    tests: tests.map((x) => ({ ...x, date, report_id: id })) }] });
const report = (id: string, note: string | null): ReportSummary => ({ id, status: "explained", lab_name: null,
  collected_at: null, created_at: "2021-03-18T10:00:00Z", rows: 1, note });
const xray: HealthRecord = { id: "x1", profile_id: "p1", kind: "imaging", title: "Chest X-ray", record_date: "2022-04-06",
  facility: "Utkal Imaging", notes: null, mime_type: "application/pdf", size_bytes: 1, created_at: "2022-04-06T10:00:00Z" };

describe("story", () => {
  const frames = [
    frame("r1", "2021-03-18", [r({ value: "5.4" }), r({ test_code: "k", test_name: "Potassium", value: "4.2", ref_low: "3.5", ref_high: "5.1" })]),
    frame("r2", "2022-04-06", [r({ value: "6.7", status: "high" }), r({ test_code: "k", test_name: "Potassium", value: "6.6", status: "critical_high", ref_low: "3.5", ref_high: "5.1" })]),
    frame("r3", "2023-04-19", [r({ value: "7.0", status: "high" })]),
    frame("r4", "2024-06-05", [r({ value: "7.6", status: "high" })]),
    frame("r5", "2025-08-20", [r({ value: "6.4", status: "high" })]),
    frame("r6", "2026-02-11", [r({ value: "6.9", status: "high" })]),
    frame("r7", "2026-08-19", [r({ value: "5.5" })]),
  ];
  const chapters = buildStory(frames, [xray], [report("r2", "Diet changed"), report("r1", null)]);
  const kinds = (i: number) => chapters[i].events.map((e) => e.kind);

  it("opens with the first report and puts records in date order after a report of the same day", () => {
    expect(chapters.map((c) => c.key)).toEqual(["r1", "r2", "x1", "r3", "r4", "r5", "r6", "r7"]);
    expect(kinds(0)).toEqual(["first"]);
    expect(chapters[2].isRecord).toBe(true);
    expect(chapters[2].frame?.report_id).toBe("r2"); // the body stays as the report before left it
  });

  it("names what left its range, what was critical, and the family's note", () => {
    expect(kinds(1)).toEqual(["critical", "out", "note"]);
    const out = chapters[1].events[1];
    expect(out.kind === "out" && out.previous?.value).toBe("5.4");
  });

  it("tells a new highest from an improvement, a setback and a return to range", () => {
    expect(kinds(3)).toEqual(["peak"]); // 7.0: the highest of three results
    expect(kinds(4)).toEqual(["peak"]); // 7.6: higher still
    expect(kinds(5)).toEqual(["better"]); // 6.4: closer to the range
    expect(kinds(6)).toEqual(["worse"]); // 6.9: further out again, but not the highest
    expect(kinds(7)).toEqual(["back", "clear"]); // 5.5: within 4.0 - 5.6 again, and nothing else is out
  });

  it("gives longer chapters more time, within a limit", () => {
    expect(chapterMs(chapters[0])).toBeLessThan(chapterMs(chapters[1]));
    expect(chapterMs({ ...chapters[1], events: Array(12).fill(chapters[1].events[0]) })).toBe(11000);
  });
});
