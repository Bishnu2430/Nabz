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
