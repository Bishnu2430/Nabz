import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { Reading, Reminder } from "../api/care";
import { daysUntil } from "../components/care/Reminders";
import { mockApi, renderRoute } from "../test/utils";

const person = {
  id: "p1", display_name: "Ramesh Mohanty", sex: "male", date_of_birth: "1968-03-14", relationship: "spouse",
  preferred_language: "en", reports: 0, latest_report_at: null, last_tested: null, attention: [],
};

const iso = (daysFromNow: number) => {
  const d = new Date();
  return new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate() + daysFromNow)).toISOString().slice(0, 10);
};

const reminder = (over: Partial<Reminder>): Reminder => ({
  id: "m1", profile_id: "p1", title: "Repeat HbA1c", test_code: "hba1c", due_on: iso(10), repeat_months: 3,
  note: "Fasting sample", sent_at: null, done_at: null, ...over });

describe("reminders", () => {
  it("counts whole calendar days", () => {
    const today = new Date(2026, 9, 1, 23, 30);
    expect([daysUntil("2026-10-01", today), daysUntil("2026-10-11", today), daysUntil("2026-09-28", today)]).toEqual([0, 10, -3]);
  });

  it("lists a person's reminders with their dates, and adds one", async () => {
    let list = [reminder({}), reminder({ id: "m2", title: "Eye check-up", test_code: null, due_on: iso(-3), repeat_months: null, note: null })];
    const calls = mockApi({
      "GET /v1/profiles": () => [person],
      "GET /v1/profiles/p1/reports": () => [],
      "GET /v1/profiles/p1/body-map": () => [],
      "GET /v1/profiles/p1/consents": () => [],
      "GET /v1/profiles/p1/reminders": () => list,
      "POST /v1/profiles/p1/reminders": (_url, init) => {
        const made = reminder({ id: "m3", ...JSON.parse(String(init.body)), repeat_months: null, note: null });
        list = [...list, made];
        return made;
      },
      "PATCH /v1/reminders/m1": () => reminder({ done_at: "2026-10-01T05:00:00Z" }),
    });
    renderRoute("/p/p1");
    const first = (await screen.findByRole("heading", { name: "Repeat HbA1c" })).closest("li")!;
    expect(within(first).getByText("in 10 days")).toBeInTheDocument();
    expect(within(first).getByText("Repeats every 3 months")).toBeInTheDocument();
    expect(within(first).getByRole("link", { name: "Add to calendar" })).toHaveAttribute("href", "/v1/reminders/m1/calendar.ics");
    expect(screen.getByText("3 days overdue")).toBeInTheDocument();
    // the tools a family keeps themselves are there before the first report
    expect(screen.getByRole("link", { name: "Home readings" })).toHaveAttribute("href", "/p/p1/readings");
    expect(screen.getByRole("link", { name: "Emergency card" })).toHaveAttribute("href", "/p/p1/card");

    await userEvent.click(within(first).getByRole("button", { name: "Done" }));
    await waitFor(() => expect(calls.find((c) => c.method === "PATCH")?.body).toEqual({ done: true }));

    await userEvent.click(screen.getByRole("button", { name: "Add a reminder" }));
    await userEvent.type(screen.getByLabelText("What to remember"), "Kidney check");
    await userEvent.type(screen.getByLabelText("On"), iso(30));
    await userEvent.click(screen.getByRole("button", { name: "Save reminder" }));
    await waitFor(() => expect(calls.find((c) => c.method === "POST")?.body).toEqual({ title: "Kidney check", due_on: iso(30) }));
    expect(await screen.findByRole("heading", { name: "Kidney check" })).toBeInTheDocument();
  });

  it("shows the next reminder on the family card", async () => {
    mockApi({ "GET /v1/profiles": () => [{ ...person, next_reminder_title: "Repeat HbA1c", next_reminder_due: iso(10) }] });
    renderRoute("/home");
    expect(await screen.findByText("Repeat HbA1c")).toBeInTheDocument();
    expect(screen.getByText(/\(in 10 days\)/)).toBeInTheDocument();
  });
});

const reading = (id: string, value: string, value2: string, taken_at: string, context: string | null = "morning"): Reading =>
  ({ id, kind: "bp", value, value2, context, note: null, taken_at });

describe("home readings", () => {
  it("states each reading against the person's own target in exact numbers", async () => {
    const now = Date.now();
    const at = (daysAgo: number) => new Date(now - daysAgo * 86_400_000).toISOString();
    const calls = mockApi({
      "GET /v1/profiles": () => [person],
      "GET /v1/profiles/p1/readings": () => [reading("a", "148.00", "92.00", at(1)), reading("b", "126.00", "78.00", at(5), "evening"),
        { id: "w", kind: "weight", value: "78.50", value2: null, context: null, note: null, taken_at: at(2) }],
      "GET /v1/profiles/p1/reading-targets": () => ({ bp: { low: null, high: "130", low2: null, high2: "80" } }),
      "POST /v1/profiles/p1/readings": () => reading("c", "132", "84", at(0)),
      "DELETE /v1/readings/b": () => undefined,
    });
    renderRoute("/p/p1/readings");
    expect(await screen.findByRole("tab", { name: "Blood pressure 2" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("Target: < 130/80 mmHg")).toBeInTheDocument();
    expect(screen.getAllByText("upper number 18 above the target 130; lower number 12 above the target 80")).toHaveLength(2);
    expect(screen.getByText("within the target < 130/80")).toBeInTheDocument();
    expect(screen.getByText("Average of 2 readings:").parentElement).toHaveTextContent("137/85 mmHg");
    expect(screen.getByText(/1 of 2 readings were outside the target < 130\/80 mmHg; the furthest was 148\/92 mmHg on/)).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText("Upper (systolic)"), "132");
    await userEvent.type(screen.getByLabelText("Lower (diastolic)"), "84");
    await userEvent.selectOptions(screen.getByLabelText("Taken"), "evening");
    await userEvent.click(screen.getByRole("button", { name: "Save reading" }));
    await waitFor(() => expect(calls.find((c) => c.method === "POST")?.body)
      .toEqual({ kind: "bp", value: 132, value2: 84, context: "evening" }));

    await userEvent.click(screen.getByRole("button", { name: /^Delete the reading 126\/78/ }));
    await waitFor(() => expect(calls.some((c) => c.method === "DELETE" && c.url === "/v1/readings/b")).toBe(true));

    await userEvent.click(screen.getByRole("tab", { name: "Weight 1" }));
    expect(screen.getAllByText("no target set")).toHaveLength(2);
    expect(screen.getByRole("heading", { name: "Weight: every reading" })).toBeInTheDocument();
  });

  it("saves the doctor's target for a kind of reading", async () => {
    const calls = mockApi({
      "GET /v1/profiles": () => [person],
      "PUT /v1/profiles/p1/reading-targets/glucose": () => ({ glucose: { low: "80", high: "130" } }),
    });
    renderRoute("/p/p1/readings?kind=glucose");
    expect(await screen.findByRole("heading", { name: "Blood sugar: no readings yet" })).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("From"), "80");
    await userEvent.type(screen.getByLabelText("To"), "130");
    await userEvent.click(screen.getByRole("button", { name: "Save target" }));
    await waitFor(() => expect(calls.find((c) => c.method === "PUT")?.body).toEqual({ low: 80, high: 130 }));
  });
});

describe("emergency card", () => {
  const card = (info: object) => ({
    person: { id: "p1", display_name: "Ramesh Mohanty", sex: "male", age: 58 },
    info: { blood_group: null, allergies: null, conditions: null, medicines: null, doctor: null, contacts: [], ...info },
    out_of_range: [{ test_code: "hba1c", test_name: "HbA1c", short_name: "HbA1c", value: "7.6", unit: "%", decimals: 1,
      status: "high", ref_low: "4.0", ref_high: "5.6", date: "2026-08-20", report_id: "r1" }],
    last_tested: "2026-08-20", qr_svg: "data:image/svg+xml;base64,AAAA", qr_text: "EMERGENCY CARD\nRamesh Mohanty, 58 y, male",
  });

  it("prints what the family typed, who to call and the exact out-of-range results", async () => {
    let info: object = { blood_group: "B+", allergies: "Penicillin",
      contacts: [{ name: "Priya Mohanty", phone: "+91 55501 23456", relation: "wife" }] };
    const calls = mockApi({
      "GET /v1/profiles/p1/emergency": () => card(info),
      "PUT /v1/profiles/p1/emergency": (_url, init) => {
        info = JSON.parse(String(init.body));
        return info;
      },
    });
    renderRoute("/p/p1/card");
    const face = await screen.findByRole("article", { name: "Emergency card" });
    expect(within(face).getByRole("heading", { name: "Ramesh Mohanty" })).toBeInTheDocument();
    expect(within(face).getByText("58 years · Male")).toBeInTheDocument();
    expect(within(face).getByText("B+")).toBeInTheDocument();
    expect(within(face).getByText("Penicillin")).toBeInTheDocument();
    expect(within(face).getByRole("link", { name: "+91 55501 23456" })).toHaveAttribute("href", "tel:+915550123456");
    expect(within(face).getByText(/36 % above the upper limit 5.6 · 20 Aug 2026/)).toBeInTheDocument();

    // the lab results can be left off the printed card
    await userEvent.click(screen.getByRole("checkbox", { name: /Print the latest lab results/ }));
    expect(within(face).queryByText("HbA1c")).not.toBeInTheDocument();

    await userEvent.type(screen.getByLabelText("Medicines"), "Metformin 500 mg twice a day");
    await userEvent.click(screen.getByRole("button", { name: "Save the card" }));
    await waitFor(() => expect(calls.find((c) => c.method === "PUT")?.body).toEqual({
      blood_group: "B+", allergies: "Penicillin", conditions: null, medicines: "Metformin 500 mg twice a day", doctor: null,
      contacts: [{ name: "Priya Mohanty", phone: "+91 55501 23456", relation: "wife" }] }));
    expect(await within(face).findByText("Metformin 500 mg twice a day")).toBeInTheDocument();
  });
});
