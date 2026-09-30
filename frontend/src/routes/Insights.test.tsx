import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { Insights, Result, TestHistory } from "../api/types";
import { niceTicks } from "../components/insights/TrendChart";
import { mockApi, renderRoute } from "../test/utils";

const result = (over: Partial<Result>): Result => ({
  observation_id: over.test_code ?? "x", report_id: "r1", date: "2026-07-04", test_code: "hb", test_name: "Haemoglobin",
  short_name: "Hb", organ: "blood", value: "14.2", unit: "g/dL", decimals: 1, ref_low: "13.0", ref_high: "17.0",
  ref_source: "report", status: "normal", critical: false, flag_disagrees: false, previous: null, change: null,
  trend: null, percentile: null, ...over,
});

const insights = (over: Partial<Insights> = {}): Insights => ({
  report: { id: "r1", status: "explaining", lab_name: "Anvaya Diagnostics", collected_at: "2026-07-04",
    created_at: "2026-07-05T10:00:00Z", rows: 3 },
  person: { id: "p1", display_name: "Ramesh", sex: "male", age: 58 },
  analysed: true,
  critical: [],
  organs: [],
  explanation: null,
  ...over,
});

const potassium = result({ test_code: "potassium", test_name: "Potassium", organ: "kidney", value: "6.6", unit: "mmol/L",
  ref_low: "3.5", ref_high: "5.1", status: "critical_high", critical: true });
const creatinine = result({
  test_code: "creatinine", test_name: "Creatinine", organ: "kidney", value: "1.21", unit: "mg/dL", decimals: 2,
  ref_low: "0.7", ref_high: "1.3", previous: { value: 1.05, date: "2025-06-04", report_id: "r0" },
  change: { fraction: 0.152, direction: "up", significant: true, rcv_down: -0.13, rcv_up: 0.153 },
  percentile: { value: 88.4, side: "within", population: "US population (NHANES 2017–2020)", sex: "male", age_band: [50, 59] },
});

describe("Insights", () => {
  it("puts the critical message before anything else", async () => {
    mockApi({
      "GET /v1/reports/r1/explanation?lang=en": () => ({ state: "none", explanation: null }),
      "GET /v1/reports/r1/insights": () => insights({
        critical: [potassium],
        organs: [
          { code: "kidney", names: { en: "Kidneys" }, status: "critical_high", results: [potassium, creatinine] },
          { code: "blood", names: { en: "Blood" }, status: "normal", results: [result({})] },
        ],
      }),
    });
    renderRoute("/r/r1");

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Contact a doctor today");
    expect(alert).toHaveTextContent("Potassium");
    const headings = screen.getAllByRole("heading").map((h) => h.textContent);
    expect(headings.indexOf("Contact a doctor today")).toBeLessThan(headings.indexOf("Kidneys"));
    expect(headings.indexOf("Kidneys")).toBeLessThan(headings.indexOf("Blood"));
    expect(screen.getByText("1 of 3 results is outside its range")).toBeInTheDocument();
  });

  it("shows change significance and a labelled population percentile", async () => {
    mockApi({
      "GET /v1/reports/r1/explanation?lang=en": () => ({ state: "none", explanation: null }),
      "GET /v1/reports/r1/insights": () => insights({
        organs: [{ code: "kidney", names: { en: "Kidneys" }, status: "normal", results: [creatinine] }],
      }),
    });
    renderRoute("/r/r1");
    expect(await screen.findByText(/\+15 % since 4 Jun 2025/)).toBeInTheDocument();
    expect(screen.getByText("more than normal variation")).toBeInTheDocument();
    expect(screen.getByText("88th percentile among US men aged 50–59")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("folds results in range behind a button", async () => {
    const normals = ["hb", "wbc", "plt", "rbc"].map((c) => result({ test_code: c, test_name: c.toUpperCase() }));
    const low = result({ test_code: "mcv", test_name: "MCV", status: "low", ref_low: "83", ref_high: "101", value: "78" });
    mockApi({
      "GET /v1/reports/r1/explanation?lang=en": () => ({ state: "none", explanation: null }),
      "GET /v1/reports/r1/insights": () => insights({
        organs: [{ code: "blood", names: { en: "Blood" }, status: "low", results: [low, ...normals] }],
      }),
    });
    renderRoute("/r/r1");
    expect(await screen.findByText("MCV")).toBeInTheDocument();
    expect(screen.queryByText("WBC")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "4 more in range" }));
    expect(screen.getByText("WBC")).toBeInTheDocument();
  });

  it("waits with the ensō until the analysis has run, and sends unconfirmed reports to review", async () => {
    mockApi({ "GET /v1/reports/r1/insights": () => insights({ analysed: false, report: { ...insights().report, status: "analysing" } }) });
    renderRoute("/r/r1");
    expect(await screen.findByText("Analysing the results…")).toBeInTheDocument();
  });
});

describe("TestHistory", () => {
  const history = (results: Result[]): TestHistory => ({
    test: { code: "hba1c", name: "HbA1c", short_name: "HbA1c", unit: "%", decimals: 1, organ: "pancreas", rcv_down: -0.059, rcv_up: 0.063 },
    person: { id: "p1", display_name: "Ramesh", sex: "male", age: 58 },
    results,
  });
  const visit = (date: string, value: string, over: Partial<Result> = {}) =>
    result({ test_code: "hba1c", test_name: "HbA1c", observation_id: date, date, value, unit: "%", ref_low: "4.0", ref_high: "6.5", ...over });

  it("explains a confirmed trend, its projection and the population comparison, with a table twin", async () => {
    const trend = { n: 4, first: "2022-06-01", last: "2025-06-01", slope_per_year: 0.3, intercept: 5.0, slope_low: 0.28,
      slope_high: 0.31, p_value: 0.083, change_fraction: 0.18, direction: "rising" as const, confirmed: true, reason: "" as const,
      projection: { kind: "leave" as const, limit: "high" as const, value: 6.5, on: "2027-06-01" } };
    const results = [visit("2022-06-01", "5.0"), visit("2023-06-01", "5.3"), visit("2024-06-01", "5.6"),
      visit("2025-06-01", "5.9", { trend, percentile: { value: 97, side: "above", population: "US population (NHANES 2017–2020)", sex: "male", age_band: [50, 59] } })];
    mockApi({ "GET /v1/profiles/p1/tests/hba1c": () => history(results) });
    renderRoute("/p/p1/tests/hba1c");

    expect(await screen.findByText("Rising by about 0.3 % a year over 3 years.")).toBeInTheDocument();
    expect(screen.getByText(/reach the upper limit \(6\.5\) around Jun 2027/)).toBeInTheDocument();
    expect(screen.getByText(/above the 95th percentile of US men aged 50–59/)).toBeInTheDocument();
    expect(screen.getByText(/a rise of more than \+6\.3 % or a fall of more than 5\.9 %/)).toBeInTheDocument();
    const rows = within(screen.getByRole("table")).getAllByRole("row");
    expect(rows).toHaveLength(5); // header + 4, newest first
    expect(rows[1]).toHaveTextContent("1 Jun 2025");
    expect(screen.getAllByRole("button", { name: /Jun 20\d\d: \d\.\d %/ })).toHaveLength(4); // focusable chart points
  });

  it("says why an unconfirmed trend isn't called", async () => {
    const trend = { n: 3, first: "2023-06-01", last: "2025-06-01", slope_per_year: 0.3, intercept: 5.0, slope_low: null,
      slope_high: null, p_value: 0.33, change_fraction: 0.12, direction: "rising" as const, confirmed: false,
      reason: "too_few" as const, projection: null };
    mockApi({ "GET /v1/profiles/p1/tests/hba1c": () => history([visit("2023-06-01", "5.0"), visit("2024-06-01", "5.3"),
      visit("2025-06-01", "5.6", { trend })]) });
    renderRoute("/p/p1/tests/hba1c");
    expect(await screen.findByText(/A fourth will show whether it's a real trend/)).toBeInTheDocument();
  });
});

describe("niceTicks", () => {
  it("returns round steps covering the range", () => {
    expect(niceTicks(0, 10)).toEqual([0, 2.5, 5, 7.5, 10]);
    expect(niceTicks(4.1, 6.9)).toEqual([4.5, 5, 5.5, 6, 6.5]);
    expect(niceTicks(3, 3)).toEqual([3]);
  });
});
