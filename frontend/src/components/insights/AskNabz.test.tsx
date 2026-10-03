import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { Question } from "../../api/ask";
import { makeQueryClient } from "../../api/queryClient";
import type { Result } from "../../api/types";
import { mockApi } from "../../test/utils";
import { ToastProvider } from "../Toast";
import { AskNabz } from "./AskNabz";

const creatinine = {
  observation_id: "o1", report_id: "r1", date: "2026-08-19", test_code: "creatinine", test_name: "Creatinine",
  short_name: "Creatinine", organ: "kidney", value: "1.46", unit: "mg/dL", decimals: 2, ref_low: "0.7", ref_high: "1.28",
  ref_source: "report", status: "high", critical: false, flag_disagrees: false, previous: null, change: null, trend: null,
  percentile: null,
} as Result;

const reply = (over: Partial<Question>): Question => ({
  id: "q1", language: "en", question: "", answer: "", mode: "knowledge", refusal: null, reason: "no_consent",
  test_codes: [], sources: [], created_at: "2026-10-03T10:00:00Z", ...over,
});

function show() {
  render(
    <QueryClientProvider client={makeQueryClient({ retry: false })}>
      <ToastProvider><AskNabz reportId="r1" profileId="p1" results={[creatinine]} /></ToastProvider>
    </QueryClientProvider>,
  );
}

describe("Ask Nabz", () => {
  it("answers from the values, says plainly when it won't, and offers questions to start with", async () => {
    const calls = mockApi({
      "POST /v1/reports/r1/ask": (_url, init) => {
        const { question } = JSON.parse(String(init.body));
        return question.startsWith("Do I have")
          ? reply({ id: "q2", question, mode: "refusal", refusal: "diagnosis",
            answer: "Nabz can't tell you whether you have a condition.\nWhat the report shows:\n• Creatinine is 1.46 mg/dL, above the lab's range (0.7–1.28)." })
          : reply({ question, test_codes: ["creatinine"], answer: "Creatinine is 1.46 mg/dL, above the lab's range (0.7–1.28).",
            sources: [{ label: "P1", title: "Creatinine Test", url: "https://medlineplus.gov/lab-tests/creatinine-test/",
              organisation: "MedlinePlus", license: "Public domain" }] });
      },
    });
    show();
    // suggestions come from the report: what is out of range, and what the worst test measures
    await userEvent.click(await screen.findByRole("button", { name: "What does Creatinine measure?" }));
    const first = (await screen.findByText("Creatinine is 1.46 mg/dL, above the lab's range (0.7–1.28).")).closest("article")!;
    expect(within(first).getByText("Built from your values and MedlinePlus.")).toBeInTheDocument();
    expect(within(first).getByRole("link", { name: "Creatinine Test" })).toHaveAttribute("href", "https://medlineplus.gov/lab-tests/creatinine-test/");
    expect(screen.getByText(/turn on “Explain with an AI service”/)).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText("Your question"), "Do I have kidney disease?");
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));
    const second = (await screen.findByText("Nabz doesn't diagnose")).closest("article")!;
    expect(within(second).getByText("Creatinine is 1.46 mg/dL, above the lab's range (0.7–1.28).")).toBeInTheDocument();
    expect(within(second).getByText("A fixed reply; no AI service was asked.")).toBeInTheDocument();
    await waitFor(() => expect(calls.filter((c) => c.method === "POST").map((c) => (c.body as { question: string }).question))
      .toEqual(["What does Creatinine measure?", "Do I have kidney disease?"]));
  });
});
