import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { Organ, Result } from "../../api/types";
import i18n from "../../i18n";
import { plainSummary } from "../../lib/plainSummary";
import { PlainSummary } from "./PlainSummary";

const result = (over: Partial<Result>): Result => ({
  observation_id: over.test_code ?? "x", report_id: "r1", date: "2026-08-02", test_code: "hb", test_name: "Haemoglobin",
  short_name: "Hb", organ: "blood", value: "14.2", unit: "g/dL", decimals: 1, ref_low: "13.0", ref_high: "17.0",
  ref_source: "report", status: "normal", critical: false, flag_disagrees: false, previous: null, change: null,
  trend: null, percentile: null, ...over,
});
const organ = (code: string, results: Result[]): Organ => ({
  code, names: { en: code, hi: code, or: code }, status: "normal", results,
});

// a full health check: "bad" cholesterol well above its range, "good" cholesterol just below it, a ratio off too,
// protein found in urine, creatinine changed since last time, the rest in range
const report = [
  organ("heart", [
    result({ test_code: "ldl", test_name: "LDL cholesterol", value: "142", ref_low: null, ref_high: "100", status: "high" }),
    result({ test_code: "hdl", test_name: "HDL cholesterol", value: "38", ref_low: "40", ref_high: "60", status: "low" }),
    result({ test_code: "chol_hdl_ratio", value: "5.6", ref_low: "3", ref_high: "5", status: "high" }),
    result({ test_code: "tg", value: "120", ref_low: null, ref_high: "150" }),
  ]),
  organ("urinary", [
    result({ test_code: "urine_protein", status: "high", answer: "trace", usual: "absent", value: "0.5", ref_low: null,
      ref_high: "0" }),
    result({ test_code: "urine_ph", value: "6", ref_low: "5", ref_high: "8" }),
  ]),
  organ("liver", [result({ test_code: "alt" })]),
  organ("kidney", [result({ test_code: "creatinine", change: { fraction: 0.3, direction: "up", significant: true,
    rcv_down: -0.2, rcv_up: 0.25 } })]),
  organ("blood", [result({}), result({ test_code: "wbc" })]),
];

afterEach(() => { void i18n.changeLanguage("en"); });

describe("plain summary", () => {
  it("names what is off in each area, the basic tests before the ratios worked out from them", () => {
    const s = plainSummary(report);
    expect(s.head).toBe("several_out");  // four of ten results
    expect(s.areas.map((a) => [a.code, a.items.map((i) => [i.lay, i.direction]), a.more])).toEqual([
      ["heart", [["ldl", "high"], ["hdl", "low_slightly"]], true],
      ["urinary", [["urine_protein", null]], false],
    ]);
    expect(s.fine).toEqual(["liver", "kidney", "blood"]);
    expect(s.changed).toEqual(["creatinine"]);
  });

  it("says a count and a percentage of the same cells once, and puts a critical result first", () => {
    const blood = organ("blood", [
      result({ test_code: "lymph_pct", value: "46", ref_low: "20", ref_high: "40", status: "high" }),
      result({ test_code: "lymph_abs", value: "3.6", ref_low: "1", ref_high: "3", status: "high" }),
    ]);
    const kidney = organ("kidney", [result({ test_code: "potassium", value: "6.8", ref_low: "3.5", ref_high: "5.1",
      status: "critical_high" })]);
    const s = plainSummary([blood, kidney]);
    expect(s.head).toBe("critical");
    expect(s.areas.map((a) => [a.code, a.items.map((i) => [i.lay, i.direction])])).toEqual([
      ["kidney", [["potassium", "far_high"]]],
      ["blood", [["lymph", "high"]]],
    ]);
  });

  it("explains each result in plain words, with no values, in every language", async () => {
    for (const lang of ["en", "hi", "or"]) {
      await i18n.changeLanguage(lang);
      const { container, unmount } = render(<PlainSummary organs={report} />);
      // names such as "LDL" stay; numbers standing on their own never appear
      expect(container.textContent).not.toMatch(/(?<![A-Za-z0-9])[0-9]|[०-९୦-୯]/);
      unmount();
    }
    await i18n.changeLanguage("en");
    render(<PlainSummary organs={report} />);
    expect(screen.getByText(
      "Your “bad” cholesterol (LDL), which can build up in the walls of blood vessels, is higher than usual."))
      .toBeInTheDocument();
    expect(screen.getByText("Your “good” cholesterol (HDL), which helps carry cholesterol away, is slightly lower than "
      + "usual.")).toBeInTheDocument();
    expect(screen.getByText("Some other results here are also outside the usual range.")).toBeInTheDocument();
    expect(screen.getByText("Protein in your urine: Trace. Usually: Absent.")).toBeInTheDocument();
    expect(screen.getByText("Your liver tests, your kidney tests and your blood count: all in the usual range."))
      .toBeInTheDocument();
    expect(screen.getByText(
      "Since your last report, your creatinine changed more than the usual day-to-day ups and downs."))
      .toBeInTheDocument();
    expect(screen.getByText(/When you see your doctor, ask about your cholesterol and blood fats and your urine test\./))
      .toBeInTheDocument();
  });
});
