import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { ReviewItem } from "../../api/staff";
import { ME, mockApi, renderRoute } from "../../test/utils";

const REVIEWER = { ...ME, role: "reviewer", totp_enabled: true };
const ADMIN = { ...ME, id: "a1", role: "admin", totp_enabled: true };

const summary = {
  explanations: { model: 3, template: 9 }, fallback_reasons: { validation: 1, no_consent: 8 }, blocked_rate: 0.25,
  questions: { refusal: 2, knowledge: 4 }, refusals: { diagnosis: 2 }, feedback: { helpful: 5, not_helpful: 1 },
  open: { explanation: 1, question: 0, feedback: 0 }, reviewed: 0,
};

const blocked: ReviewItem = {
  kind: "explanation", id: "e1", created_at: "2026-10-02T10:00:00Z", language: "en", age_band: "50–59", sex: "male",
  values: [{ test: "Creatinine", value: 1.46, unit: "mg/dL", range_low: 0.7, range_high: 1.28, status: "high" }],
  question: null, feedback: null, shown: "Creatinine is 1.46 mg/dL, above the lab's range.",
  blocked: { text: "You have kidney disease.", spans: [{ start: 0, end: 15, code: "diagnosis" }] },
  problems: [{ code: "diagnosis", detail: "'You have kidney'" }], reason: "validation", refusal: null, mode: "template",
  review: null,
};

describe("the safety review console", () => {
  it("shows what the checks stopped, marked, and records the reviewer's verdict", async () => {
    let reviewed = false;
    const calls = mockApi({
      "GET /v1/auth/me": () => REVIEWER,
      "GET /v1/profiles": () => [],
      "GET /v1/review/summary": () => summary,
      "GET /v1/review/queue?state=open": () => (reviewed ? [] : [blocked]),
      "POST /v1/review/items/explanation/e1": () => {
        reviewed = true;
        return { verdict: "correct", note: "Rightly stopped", reviewer: "asha@example.com", at: "2026-10-03T10:00:00Z" };
      },
    });
    // a reviewer with no family of their own starts at the console
    const { router } = renderRoute("/home");
    expect(await screen.findByRole("heading", { name: "Safety review" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/review");
    expect(await screen.findByText("25 %")).toBeInTheDocument();

    const card = (await screen.findByText("Blocked explanation")).closest("div.card") as HTMLElement;
    expect(within(card).getByText("You have kidney", { selector: "mark" })).toHaveAttribute("title", "Diagnosis");
    expect(within(card).getByText(/aged 50–59 · Male/)).toBeInTheDocument();

    await userEvent.type(within(card).getByLabelText("Your note"), "Rightly stopped");
    await userEvent.click(within(card).getByRole("button", { name: "Rightly blocked" }));
    await waitFor(() => expect(calls.find((c) => c.method === "POST")?.body).toEqual({ verdict: "correct", note: "Rightly stopped" }));
    expect(await screen.findByText(/Nothing to review/)).toBeInTheDocument();
  });

  it("tries the checks on any text", async () => {
    mockApi({
      "GET /v1/auth/me": () => REVIEWER,
      "GET /v1/review/summary": () => summary,
      "POST /v1/review/check": () => ({ text: "There is nothing to worry about.", spans: [{ start: 9, end: 31, code: "reassurance" }],
        problems: [{ code: "reassurance", detail: "'nothing to worry about'" }], as_question: null }),
    });
    renderRoute("/review?tab=check");
    await userEvent.click(await screen.findByRole("button", { name: "There is nothing to worry about." }));
    expect(await screen.findByText("nothing to worry about", { selector: "mark" })).toBeInTheDocument();
    expect(screen.getByText("Would be blocked for:")).toBeInTheDocument();
    expect(screen.getByText("Not stopped by the question rules.")).toBeInTheDocument();
  });

  it("is closed to anyone who isn't a reviewer", async () => {
    mockApi({ "GET /v1/auth/me": () => ME });
    renderRoute("/review");
    expect(await screen.findByRole("heading", { name: "This area is for staff" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Safety review" })).not.toBeInTheDocument();
  });
});

describe("the system pages", () => {
  it("lets an admin change another account's role but not their own", async () => {
    const calls = mockApi({
      "GET /v1/auth/me": () => ADMIN,
      "GET /v1/admin/users": () => [
        { id: "a1", email: "admin@nabz.local", role: "admin", verified: true, totp: true, locked: false,
          created_at: "2026-10-01T10:00:00Z", last_login_at: "2026-10-03T10:00:00Z", sessions: 1, profiles: 0 },
        { id: "u2", email: "family@nabz.local", role: "user", verified: true, totp: false, locked: true,
          created_at: "2026-10-01T10:00:00Z", last_login_at: null, sessions: 2, profiles: 5 },
      ],
      "PATCH /v1/admin/users/u2": () => ({ id: "u2" }),
      "POST /v1/admin/users/u2/unlock": () => ({ id: "u2" }),
    });
    renderRoute("/admin?tab=users");
    expect(await screen.findByRole("combobox", { name: "Role of admin@nabz.local" })).toBeDisabled();
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Role of family@nabz.local" }), "reviewer");
    await waitFor(() => expect(calls.find((c) => c.method === "PATCH")?.body).toEqual({ role: "reviewer" }));
    await userEvent.click(screen.getByRole("button", { name: "Unlock" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/v1/admin/users/u2/unlock")).toBe(true));
    expect(screen.getByRole("button", { name: "Sign out (2 devices)" })).toBeInTheDocument();
  });

  it("shows a reviewer the system's health but not its users", async () => {
    mockApi({
      "GET /v1/auth/me": () => REVIEWER,
      "GET /v1/admin/overview": () => ({
        health: { database: true, worker_last_job: null, jobs: { failed: 2 }, model: true, voice: false, embeddings: true, mail: "smtp" },
        counts: { users: { user: 3, reviewer: 1 }, verified: 4, two_step: 1, people: 5, reports: { explained: 38 }, records: 5,
          readings: 243, reminders: 9, share_links: 1, explanations: { template: 38 }, questions: { refusal: 3 }, tests: 70, passages: 436 },
        activity: Array.from({ length: 14 }, (_, i) => ({ day: `2026-09-${String(10 + i).padStart(2, "0")}`, uploads: i % 3, explanations: 1, questions: 0 })),
      }),
    });
    renderRoute("/admin");
    expect(await screen.findByText("2 failed jobs")).toBeInTheDocument();
    expect(screen.getByText("243")).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: /Users/ })).not.toBeInTheDocument();
  });
});
