import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { BodyMapFrame, Insights, OrganHistory, Result, ResultBrief } from "../../api/types";
import { mockApi, renderRoute } from "../../test/utils";
import { FOCUS_3D, ORGAN_ORDER, SHAPES_2D } from "./organs";

const result = (over: Partial<Result>): Result => ({
  observation_id: over.test_code ?? "x", report_id: "r1", date: "2026-07-04", test_code: "hb", test_name: "Haemoglobin",
  short_name: "Hb", organ: "blood", value: "14.2", unit: "g/dL", decimals: 1, ref_low: "13.0", ref_high: "17.0",
  ref_source: "report", status: "normal", critical: false, flag_disagrees: false, previous: null, change: null,
  trend: null, percentile: null, ...over,
});

const creatinine = result({ test_code: "creatinine", test_name: "Creatinine", short_name: "Creat", organ: "kidney",
  value: "1.6", unit: "mg/dL", ref_low: "0.7", ref_high: "1.3", status: "high",
  previous: { value: 1.2, date: "2025-06-04", report_id: "r0" },
  change: { fraction: 0.333, direction: "up", significant: true, rcv_down: -0.13, rcv_up: 0.15 } });

const insights: Insights = {
  report: { id: "r1", status: "explained", lab_name: "Anvaya Diagnostics", collected_at: "2026-07-04",
    created_at: "2026-07-05T10:00:00Z", rows: 2, note: null },
  person: { id: "p1", display_name: "Ramesh", sex: "male", age: 58 },
  analysed: true,
  critical: [],
  organs: [
    { code: "kidney", names: { en: "Kidneys" }, status: "high", results: [creatinine] },
    { code: "blood", names: { en: "Blood" }, status: "normal", results: [result({})] },
  ],
  explanation: null,
};

const history = (code: string, results: Result[]): OrganHistory => ({
  code, names: { en: code }, person: insights.person,
  tests: [{ test: { code: results[0].test_code, name: results[0].test_name, short_name: results[0].short_name,
    unit: results[0].unit ?? "", decimals: 1, organ: code, rcv_down: null, rcv_up: null }, results }],
});

describe("body map", () => {
  it("names the worst result exactly and opens an organ panel with its numbers", async () => {
    mockApi({
      "GET /v1/reports/r1/insights": () => insights,
      "GET /v1/profiles/p1/organs/kidney": () => history("kidney", [
        result({ ...creatinine, report_id: "r0", date: "2025-06-04", value: "1.2", status: "normal", change: null,
          previous: null }), creatinine]),
      "GET /v1/profiles/p1/organs/blood": () => history("blood", [result({})]),
      "GET /v1/reports/r1/explanation?lang=en": () => ({
        state: "ready",
        explanation: { id: "e1", language: "en", source: "template", reason: "no_consent", summary: "",
          per_test: [{ test_code: "creatinine", status: "high", what_it_measures: "Kidney filtering.",
            what_this_result_means: "Your creatinine is above the lab's range.", citations: [] }],
          doctor_questions: [], disclaimer_key: "not_a_diagnosis_v1", sources: [], has_audio: false,
          created_at: "2026-07-05T10:00:00Z" },
      }),
    });
    renderRoute("/r/r1");

    expect(await screen.findByText("This device can't show the 3D body, so the flat map is shown.")).toBeInTheDocument();
    const list = screen.getByRole("list", { name: "Organ systems" });
    const kidneys = within(list).getByRole("button", { name: /Kidneys/ });
    expect(kidneys).toHaveTextContent("Creat 1.6 mg/dL, 23 % above the upper limit 1.3");
    expect(within(list).getByRole("button", { name: /Blood/ })).toHaveTextContent("In range: Hb 14.2 g/dL");

    await userEvent.click(kidneys);
    expect(await screen.findByRole("heading", { name: "Outside the range" })).toBeInTheDocument();
    expect(screen.getAllByText("23 % above the upper limit 1.3").length).toBeGreaterThan(0);
    expect(screen.getByText(/\+33 % since 4 Jun 2025 \(was 1\.2 mg\/dL\)/)).toHaveTextContent("more than normal variation");
    expect(screen.getByText("Lab's range: 0.7 – 1.3")).toBeInTheDocument();
    // the excerpt in the panel, and the full explanation further down
    expect(await screen.findAllByText("Your creatinine is above the lab's range.")).toHaveLength(2);
    // the results below show only this system until "Show all"
    expect(screen.getByText("Showing Kidneys")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Blood", level: 2 })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /All organ systems/ }));
    const organ = screen.getByRole("button", { name: "Blood: In range" });
    organ.focus();
    await userEvent.keyboard("{Enter}");
    expect(await screen.findByRole("heading", { name: "In range" })).toBeInTheDocument();
  });

  it("replays a person's reports and filters their reports to the chosen system", async () => {
    const brief = (over: Partial<ResultBrief>): ResultBrief => ({
      test_code: "creatinine", test_name: "Creatinine", short_name: "Creat", value: "1.1", unit: "mg/dL", decimals: 2,
      status: "normal", ref_low: "0.7", ref_high: "1.3", date: "2025-06-04", report_id: "r0", ...over });
    const frames: BodyMapFrame[] = [
      { report_id: "r0", date: "2025-06-04", lab_name: null, organs: [
        { code: "kidney", status: "normal", out_of_range: 0, results: 1, tests: [brief({})] }] },
      { report_id: "r1", date: "2026-07-04", lab_name: null, organs: [
        { code: "kidney", status: "high", out_of_range: 1, results: 1,
          tests: [brief({ value: "1.62", status: "high", date: "2026-07-04", report_id: "r1" })] },
        { code: "blood", status: "normal", out_of_range: 0, results: 1,
          tests: [brief({ test_code: "hb", test_name: "Haemoglobin", short_name: "Hb", value: "14.1", unit: "g/dL",
            ref_low: "13", ref_high: "17", date: "2026-07-04", report_id: "r1" })] }] },
    ];
    const report = (id: string, date: string) => ({ id, status: "explained", lab_name: null, collected_at: date,
      created_at: `${date}T10:00:00Z`, rows: 3, note: null, out_of_range: [] });
    mockApi({
      "GET /v1/profiles": () => [{ id: "p1", display_name: "Ramesh", sex: "male", date_of_birth: null,
        relationship: "parent", preferred_language: "en", reports: 2, latest_report_at: "2026-07-05T10:00:00Z" }],
      "GET /v1/profiles/p1/reports": () => [report("r1", "2026-07-04"), report("r0", "2025-06-04")],
      "GET /v1/profiles/p1/body-map": () => frames,
      "GET /v1/profiles/p1/watch": () => [],
      "GET /v1/profiles/p1/consents": () => [],
      "GET /v1/profiles/p1/records": () => [],
      "GET /v1/profiles/p1/organs/kidney": () => history("kidney", [
        result({ test_code: "creatinine", test_name: "Creatinine", value: "1.1", report_id: "r0", date: "2025-06-04",
          ref_low: "0.7", ref_high: "1.3", unit: "mg/dL" })]),
    });
    renderRoute("/p/p1");

    const timeline = await screen.findByRole("list", { name: "Reports by date" });
    expect(within(timeline).getByRole("button", { name: "4 Jul 2026" })).toHaveAttribute("aria-current", "step");
    const systems = screen.getByRole("list", { name: "Organ systems" });
    expect(within(systems).getByRole("button", { name: /Kidneys/ })).toHaveTextContent("Creat 1.62 mg/dL, 25 % above");

    await userEvent.click(within(timeline).getByRole("button", { name: "4 Jun 2025" }));
    await userEvent.click(within(screen.getByRole("list", { name: "Organ systems" })).getByRole("button", { name: /Kidneys/ }));
    expect(await screen.findByRole("link", { name: /Open the report of 4 Jun 2025/ })).toHaveAttribute("href", "/r/r0");
    // both reports have kidney results, each shown with its value
    expect(screen.getByText("Showing Kidneys")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Creatinine 1.62 mg\/dL, 25 % above/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Creatinine 1.10 mg\/dL, within 0.7 – 1.3/ })).toBeInTheDocument();
  });

  it("draws every organ system in both views", () => {
    for (const code of ORGAN_ORDER) {
      expect(SHAPES_2D[code].length).toBeGreaterThan(0);
      expect(FOCUS_3D[code]).toHaveLength(3);
    }
  });
});
