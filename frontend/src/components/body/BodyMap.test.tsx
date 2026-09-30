import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { BodyMapFrame, Insights, Result } from "../../api/types";
import { mockApi, renderRoute } from "../../test/utils";
import { FOCUS_3D, ORGAN_ORDER, SHAPES_2D } from "./organs";

const result = (over: Partial<Result>): Result => ({
  observation_id: over.test_code ?? "x", report_id: "r1", date: "2026-07-04", test_code: "hb", test_name: "Haemoglobin",
  short_name: "Hb", organ: "blood", value: "14.2", unit: "g/dL", decimals: 1, ref_low: "13.0", ref_high: "17.0",
  ref_source: "report", status: "normal", critical: false, flag_disagrees: false, previous: null, change: null,
  trend: null, percentile: null, ...over,
});

const creatinine = result({ test_code: "creatinine", test_name: "Creatinine", organ: "kidney", value: "1.6",
  unit: "mg/dL", ref_low: "0.7", ref_high: "1.3", status: "high" });

const insights: Insights = {
  report: { id: "r1", status: "explained", lab_name: "Anvaya Diagnostics", collected_at: "2026-07-04",
    created_at: "2026-07-05T10:00:00Z", rows: 2 },
  person: { id: "p1", display_name: "Ramesh", sex: "male", age: 58 },
  analysed: true,
  critical: [],
  organs: [
    { code: "kidney", names: { en: "Kidneys" }, status: "high", results: [creatinine] },
    { code: "blood", names: { en: "Blood" }, status: "normal", results: [result({})] },
  ],
  explanation: null,
};

describe("body map", () => {
  it("falls back to the flat map without WebGL 2 and opens an organ's card from the list", async () => {
    mockApi({
      "GET /v1/reports/r1/insights": () => insights,
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
    expect(kidneys).toHaveTextContent("1 of 1 result out of range");
    expect(within(list).getByRole("button", { name: /Blood/ })).toHaveTextContent("1 result, in range");
    await userEvent.click(kidneys);
    expect(kidneys).toHaveAttribute("aria-pressed", "true");
    // the excerpt beside the body, and the full explanation further down
    expect(await screen.findAllByText("Your creatinine is above the lab's range.")).toHaveLength(2);
    expect(screen.getByRole("link", { name: "Read the full explanation" })).toHaveAttribute("href", "#explanation");
    expect(screen.getByRole("button", { name: "Whole body" })).toBeInTheDocument();

    // the drawing is keyboard-operable too, and names each system with its status
    const organ = screen.getByRole("button", { name: "Blood: In range" });
    organ.focus();
    await userEvent.keyboard("{Enter}");
    expect(within(list).getByRole("button", { name: /Blood/ })).toHaveAttribute("aria-pressed", "true");
  });

  it("replays a person's reports on the timeline", async () => {
    const frames: BodyMapFrame[] = [
      { report_id: "r0", date: "2025-06-04", lab_name: null, organs: [{ code: "kidney", status: "normal", out_of_range: 0, results: 3 }] },
      { report_id: "r1", date: "2026-07-04", lab_name: null, organs: [{ code: "kidney", status: "high", out_of_range: 1, results: 3 }] },
    ];
    mockApi({
      "GET /v1/profiles": () => [{ id: "p1", display_name: "Ramesh", sex: "male", date_of_birth: null,
        relationship: "parent", preferred_language: "en", reports: 2, latest_report_at: "2026-07-05T10:00:00Z" }],
      "GET /v1/profiles/p1/reports": () => [{ id: "r1", status: "explained", lab_name: null, collected_at: "2026-07-04",
        created_at: "2026-07-05T10:00:00Z", rows: 3 }],
      "GET /v1/profiles/p1/body-map": () => frames,
      "GET /v1/profiles/p1/watch": () => [],
      "GET /v1/profiles/p1/consents": () => [],
    });
    renderRoute("/p/p1");

    const timeline = await screen.findByRole("list", { name: "Reports by date" });
    const latest = within(timeline).getByRole("button", { name: "4 Jul 2026" });
    expect(latest).toHaveAttribute("aria-current", "step");
    const systems = screen.getByRole("list", { name: "Organ systems" });
    expect(within(systems).getByRole("button", { name: /Kidneys.*High/ })).toBeInTheDocument();

    await userEvent.click(within(timeline).getByRole("button", { name: "4 Jun 2025" }));
    await userEvent.click(within(systems).getByRole("button", { name: /Kidneys.*In range/ }));
    expect(screen.getByText(/On 4 Jun 2025/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open this report" })).toHaveAttribute("href", "/r/r0");
    expect(screen.getByRole("button", { name: "Play" })).toBeInTheDocument();
  });

  it("draws every organ system in both views", () => {
    for (const code of ORGAN_ORDER) {
      expect(SHAPES_2D[code].length).toBeGreaterThan(0);
      expect(FOCUS_3D[code]).toHaveLength(3);
    }
  });
});
