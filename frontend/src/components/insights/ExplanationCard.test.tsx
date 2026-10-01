import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { Explanation, Insights } from "../../api/types";
import { mockApi, renderRoute } from "../../test/utils";

const insights: Insights = {
  report: { id: "r1", status: "explained", lab_name: "Anvaya Diagnostics", collected_at: "2026-07-04",
    created_at: "2026-07-05T10:00:00Z", rows: 1 },
  person: { id: "p1", display_name: "Asha", sex: "female", age: 52 },
  analysed: true,
  critical: [],
  organs: [{
    code: "blood", names: { en: "Blood" }, status: "low", results: [{
      observation_id: "o1", report_id: "r1", date: "2026-07-04", test_code: "hb", test_name: "Haemoglobin",
      short_name: "Hb", organ: "blood", value: "11.2", unit: "g/dL", decimals: 1, ref_low: "12.0", ref_high: "15.0",
      ref_source: "report", status: "low", critical: false, flag_disagrees: false, previous: null, change: null,
      trend: null, percentile: null,
    }],
  }],
  explanation: null,
};

const explanation = (over: Partial<Explanation> = {}): Explanation => ({
  id: "e1", language: "en", source: "model", reason: null,
  summary: "One of your results is outside the lab's range.",
  per_test: [{ test_code: "hb", status: "low", what_it_measures: "Haemoglobin carries oxygen.",
    what_this_result_means: "Your result is below the lab's range.", citations: ["P1"] }],
  doctor_questions: ["What could explain my low haemoglobin?", "Should it be repeated?"],
  disclaimer_key: "not_a_diagnosis_v1",
  sources: [{ label: "P1", title: "Hemoglobin Test", url: "https://medlineplus.gov/lab-tests/hemoglobin-test",
    organisation: "US National Library of Medicine, MedlinePlus", license: "Public domain" }],
  has_audio: false, created_at: "2026-07-05T10:00:00Z", ...over,
});

describe("ExplanationCard", () => {
  it("shows the checked explanation with its sources and the not-a-diagnosis line", async () => {
    mockApi({
      "GET /v1/reports/r1/insights": () => insights,
      "GET /v1/reports/r1/explanation?lang=en": () => ({ state: "ready", explanation: explanation() }),
    });
    renderRoute("/r/r1");
    expect(await screen.findByText("One of your results is outside the lab's range.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Haemoglobin", level: 3 })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "[1]" })).toHaveAttribute("href", "#src-1");
    expect(screen.getByRole("link", { name: "Hemoglobin Test" })).toHaveAttribute("href",
      "https://medlineplus.gov/lab-tests/hemoglobin-test");
    expect(screen.getByText(/It is not a diagnosis/)).toBeInTheDocument();
    expect(screen.queryByText(/built from your values only/)).not.toBeInTheDocument();
  });

  it("offers the fuller explanation after consent, and says exactly what would be sent", async () => {
    const calls = mockApi({
      "GET /v1/reports/r1/insights": () => insights,
      "GET /v1/reports/r1/explanation?lang=en": () => ({ state: "ready",
        explanation: explanation({ source: "template", reason: "no_consent", sources: [] }) }),
      "PUT /v1/profiles/p1/consents/external_ai": () => ({ purpose: "external_ai", granted: true, granted_at: "x" }),
      "POST /v1/reports/r1/explanation": () => ({ state: "pending", explanation: null }),
    });
    renderRoute("/r/r1");
    expect(await screen.findByText(/no name, no dates/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Allow and write it" }));
    await waitFor(() => expect(calls.some((c) => c.method === "POST")).toBe(true));
    expect(calls.find((c) => c.method === "PUT")?.body).toEqual({ granted: true });
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({ language: "en", regenerate: true });
  });

  it("asks for voice consent before the first narration", async () => {
    let voice = false;
    const calls = mockApi({
      "GET /v1/reports/r1/insights": () => insights,
      "GET /v1/reports/r1/explanation?lang=en": () => ({ state: "ready", explanation: explanation() }),
      "POST /v1/explanations/e1/audio": () => (voice ? { url: "/v1/explanations/e1/audio" }
        : new Response(JSON.stringify({ detail: "Narration needs consent to voice processing.", consent: "voice" }),
          { status: 409, headers: { "Content-Type": "application/problem+json" } })),
      "PUT /v1/profiles/p1/consents/voice": () => { voice = true; return { purpose: "voice", granted: true, granted_at: "x" }; },
    });
    renderRoute("/r/r1");
    await userEvent.click(await screen.findByRole("button", { name: "Listen" }));
    await userEvent.click(await screen.findByRole("button", { name: "Allow and listen" }));
    await waitFor(() => expect(document.querySelector("audio")).not.toBeNull());
    expect(calls.filter((c) => c.method === "POST")).toHaveLength(2);
  });
});

describe("reading layout", () => {
  const twoOut: Insights = {
    ...insights,
    organs: [{
      code: "blood", names: { en: "Blood" }, status: "low", results: [
        insights.organs[0].results[0],
        { ...insights.organs[0].results[0], observation_id: "o2", test_code: "wbc", test_name: "White blood cell count",
          short_name: "WBC", value: "7.1", unit: "10^3/µL", ref_low: "4.0", ref_high: "10.0", status: "normal" },
      ],
    }],
  };
  const summary = [
    "These results are outside the lab's range:",
    "• Haemoglobin is 11.2 g/dL; the lab's range is 12–15. A low Haemoglobin result can go along with symptoms such as tiredness or pale skin.",
    "Talk to your doctor about these results.",
  ].join("\n");

  it("turns each out-of-range line into a card and folds the rest", async () => {
    mockApi({
      "GET /v1/reports/r1/insights": () => twoOut,
      "GET /v1/reports/r1/explanation?lang=en": () => ({ state: "ready", explanation: explanation({
        summary, source: "template", reason: "validation",
        per_test: [
          { test_code: "hb", status: "low", what_it_measures: "Haemoglobin carries oxygen.",
            what_this_result_means: "Below the lab's range.", citations: [] },
          { test_code: "wbc", status: "normal", what_it_measures: "White cells fight infection.",
            what_this_result_means: "Within the lab's range.", citations: [] },
        ] }) }),
    });
    renderRoute("/r/r1");

    // the card shows the number against its range and what the result can go along with; the value isn't repeated
    expect(await screen.findByRole("heading", { name: "Haemoglobin", level: 3 })).toBeInTheDocument();
    expect(screen.getByText("A low Haemoglobin result can go along with symptoms such as tiredness or pale skin."))
      .toBeInTheDocument();
    expect(screen.queryByText(/Haemoglobin is 11.2 g\/dL; the lab's range/)).not.toBeInTheDocument();
    expect(screen.getAllByText("6.7 % below the lower limit 12").length).toBeGreaterThan(0);
    expect(screen.getByText("Talk to your doctor about these results.")).toBeInTheDocument();
    expect(screen.getByText("Built from your confirmed values.")).toBeInTheDocument();

    // the in-range result is one line that unfolds
    const more = screen.getByRole("button", { name: /White blood cell count/ });
    expect(more).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(more);
    expect(more).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("White cells fight infection.")).toBeInTheDocument();
  });

  it("highlights a result on the original report and finds the card from the page", async () => {
    mockApi({
      "GET /v1/reports/r1/insights": () => twoOut,
      "GET /v1/reports/r1/explanation?lang=en": () => ({ state: "ready", explanation: explanation({ summary }) }),
      "GET /v1/reports/r1": () => ({
        id: "r1", profile_id: "p1", status: "explained", lab_name: "Anvaya Diagnostics", collected_at: "2026-07-04",
        created_at: "2026-07-05T10:00:00Z", needs_attention: 0, unmapped: 0, confidence_threshold: 0.8,
        pages: [{ page_no: 0, width: 595, height: 842 }],
        observations: [{ id: "o1", raw_name: "Haemoglobin", raw_value: "11.2", raw_unit: "g/dL", raw_range: "12 - 15",
          raw_flag: "L", section: "cbc", test_code: "hb", test_name: "Haemoglobin", value: "11.2", unit: "g/dL",
          ref_low: "12", ref_high: "15", ref_source: "report", confidence: 0.99, needs_attention: false,
          match_method: "exact", candidates: [], bbox: { page: 0, x0: 40, top: 200, x1: 550, bottom: 212 }, edited: false }],
      }),
    });
    renderRoute("/r/r1");
    expect(await screen.findByRole("heading", { name: "The report" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open the original/ })).toHaveAttribute("href", "/v1/reports/r1/file");
    const show = await screen.findByRole("button", { name: "Show on the report" });
    await userEvent.click(show);
    expect(show).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByAltText(/Report page 1/)).toBeInTheDocument();
  });
});
