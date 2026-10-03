import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { mockApi, renderRoute } from "../test/utils";

const asha = {
  id: "p1", display_name: "Asha", sex: "female", date_of_birth: null, relationship: "self",
  preferred_language: "en", reports: 0, latest_report_at: null,
};

describe("Home", () => {
  it("shows a card per person", async () => {
    mockApi({ "GET /v1/profiles": () => [{ ...asha, reports: 2, latest_report_at: "2026-09-02T10:00:00Z" }] });
    renderRoute("/home");
    expect(await screen.findByRole("heading", { name: "Asha" })).toBeInTheDocument();
    expect(screen.getByText(/2 reports/)).toBeInTheDocument();
  });
});

describe("the first-run walkthrough", () => {
  it("leads an empty account from language to the first report", async () => {
    let people: object[] = [];
    const calls = mockApi({
      "GET /v1/profiles": () => people,
      "POST /v1/profiles": () => {
        people = [asha];
        return asha;
      },
      "GET /v1/profiles/p1/consents": () => [],
      "POST /v1/profiles/p1/sample-report": () => ({ report_id: "r9", status: "queued" }),
      "GET /v1/reports/r9": () => ({ id: "r9", profile_id: "p1", status: "processing", lab_name: null, collected_at: null,
        created_at: "2026-10-01T10:00:00Z", pages: [], observations: [], needs_attention: 0, unmapped: 0,
        confidence_threshold: 0.8 }),
    });
    const { router } = renderRoute("/home");

    // 1. language
    expect(await screen.findByRole("heading", { name: "Choose your language" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "English" })).toHaveAttribute("aria-checked", "true");
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    // 2. what Nabz is and is not: it has to be acknowledged
    expect(screen.getByRole("heading", { name: "What Nabz is, and is not" })).toBeInTheDocument();
    expect(screen.getByText("Diagnose, or name a disease.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Continue" })).toBeDisabled();
    await userEvent.click(screen.getByLabelText(/I understand that Nabz explains results/));
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    // 3. the first person, with their consent
    await userEvent.type(screen.getByLabelText("Name"), "Asha");
    await userEvent.click(screen.getByRole("button", { name: "Add person" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Consent is needed");
    expect(calls.some((c) => c.method === "POST")).toBe(false);
    await userEvent.click(screen.getByLabelText(/I agree that Nabz may read/));
    await userEvent.click(screen.getByRole("button", { name: "Add person" }));
    await waitFor(() => expect(calls.find((c) => c.method === "POST")?.body)
      .toMatchObject({ display_name: "Asha", consent_processing: true }));

    // 4. the two optional choices, off until turned on
    expect(await screen.findByRole("heading", { name: "Two choices for Asha" })).toBeInTheDocument();
    expect(await screen.findByRole("switch", { name: /Explain with an AI service/ })).not.toBeChecked();
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    // 5. their own report, or the sample
    expect(screen.getByRole("heading", { name: "The first report" })).toBeInTheDocument();
    expect(router.state.location.search).toBe("?step=5&person=p1");
    await userEvent.click(screen.getByRole("button", { name: "Use the sample" }));
    expect(await screen.findByText("Reading the report…")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "POST" && c.url === "/v1/profiles/p1/sample-report")).toBe(true);
  });

  it("waits at the first person when a later step is opened without one", async () => {
    mockApi({ "GET /v1/profiles": () => [asha] });
    renderRoute("/welcome?step=5");
    expect(await screen.findByRole("heading", { name: "Who is the first report for?" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Continue with Asha" })).toBeInTheDocument();
  });
});
