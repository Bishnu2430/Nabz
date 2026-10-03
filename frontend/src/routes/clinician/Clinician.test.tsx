import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { Grant, Note, Registration } from "../../api/clinicians";
import type { Result } from "../../api/types";
import { ME, mockApi, problem, renderRoute } from "../../test/utils";

const DOCTOR = { ...ME, id: "d1", email: "anjali@example.com", role: "clinician" };
const ADMIN = { ...ME, id: "a1", role: "admin", totp_enabled: true };
const REG = { full_name: "Dr. Anjali Rath", registration_no: "OCMR 40213", council: "Odisha Council of Medical Registration",
  specialty: "General medicine" };

const hba1c: Result = {
  observation_id: "o1", report_id: "r1", date: "2026-08-19", test_code: "hba1c", test_name: "HbA1c", short_name: "HbA1c",
  organ: "pancreas", value: "7.6", unit: "%", decimals: 1, ref_low: "4.0", ref_high: "5.6", ref_source: "report",
  status: "high", critical: false, flag_disagrees: false, previous: null, change: null, trend: null, percentile: null,
};
const view = (notes: Note[]) => ({
  person: { display_name: "Ramesh Mohanty", sex: "male", age: 58 }, lab_name: "Anvaya Diagnostics",
  collected_at: "2026-08-19", note: "Fasting sample", critical: [],
  organs: [{ code: "pancreas", names: { en: "Pancreas" }, status: "high", results: [hba1c] }], questions: [], notes,
});
const note = (text: string): Note => ({ id: "n1", text, created_at: "2026-10-03T09:30:00Z", clinician_name: "Dr. Anjali Rath" });

describe("a doctor on Nabz", () => {
  it("registers, and sees nothing shared until an admin has checked the registration", async () => {
    let reg: Registration | null = null;
    const calls = mockApi({
      "GET /v1/auth/me": () => DOCTOR,
      "GET /v1/profiles": () => [],
      "GET /v1/clinician/me": () => reg,
      "PUT /v1/clinician/me": (_, init) => {
        reg = { ...JSON.parse(String(init.body)), verified_at: null };
        return reg;
      },
    });
    // a doctor with no family of their own starts at their own page
    const { router } = renderRoute("/home");
    expect(await screen.findByRole("heading", { name: "Reports shared with you" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/clinician");
    expect(screen.getByText(/Add your medical-council registration first/)).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText("Full name, as registered"), REG.full_name);
    await userEvent.type(screen.getByLabelText("Registration number"), REG.registration_no);
    await userEvent.type(screen.getByLabelText("Medical council"), REG.council);
    await userEvent.click(screen.getByRole("button", { name: "Send for checking" }));

    await waitFor(() => expect(calls.find((c) => c.method === "PUT")?.body).toEqual({ ...REG, specialty: null }));
    expect(await screen.findByText("Not checked yet")).toBeInTheDocument();
    expect(screen.getByText(/waiting to be checked/)).toBeInTheDocument();
    expect(calls.some((c) => c.url === "/v1/clinician/shared")).toBe(false);
  });

  it("opens a shared report with exact values and leaves the family a note", async () => {
    let notes: Note[] = [];
    const calls = mockApi({
      "GET /v1/auth/me": () => DOCTOR,
      "GET /v1/clinician/me": () => ({ ...REG, verified_at: "2026-10-01T10:00:00Z" }),
      "GET /v1/clinician/shared": () => [{ report_id: "r1", person: { display_name: "Ramesh Mohanty", sex: "male", age: 58 },
        lab_name: "Anvaya Diagnostics", collected_at: "2026-08-19", shared_at: "2026-10-02T10:00:00Z", notes: notes.length }],
      "GET /v1/clinician/reports/r1": () => view(notes),
      "POST /v1/clinician/reports/r1/notes": (_, init) => {
        notes = [note(JSON.parse(String(init.body)).text)];
        return notes[0];
      },
    });
    renderRoute("/clinician");
    expect(await screen.findByText("Checked on 1 Oct 2026")).toBeInTheDocument();
    await userEvent.click(await screen.findByRole("link", { name: /Ramesh Mohanty/ }));

    expect(await screen.findByRole("heading", { name: "Ramesh Mohanty" })).toBeInTheDocument();
    expect(screen.getByText("7.6 %")).toBeInTheDocument();
    expect(screen.getByText(/36 % above the upper limit 5.6/)).toBeInTheDocument();
    expect(screen.getByText("“Fasting sample”", { exact: false })).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText("Add a note"), "Please repeat the HbA1c test in three months.");
    await userEvent.click(screen.getByRole("button", { name: "Add the note" }));
    await waitFor(() => expect(calls.find((c) => c.method === "POST")?.body).toEqual({ text: "Please repeat the HbA1c test in three months." }));
    expect(await screen.findByText("Please repeat the HbA1c test in three months.", { selector: "blockquote" })).toBeInTheDocument();
  });

  it("says plainly when a family has withdrawn the report", async () => {
    mockApi({
      "GET /v1/auth/me": () => DOCTOR,
      "GET /v1/clinician/reports/r9": () => problem(404, { detail: "Report not found." }),
    });
    renderRoute("/clinician/r/r9");
    expect(await screen.findByRole("heading", { name: "This report is no longer shared with you" })).toBeInTheDocument();
  });

  it("is a page only doctors can open", async () => {
    mockApi({ "GET /v1/profiles": () => [] });
    renderRoute("/clinician");
    expect(await screen.findByRole("heading", { name: "This page is for doctors" })).toBeInTheDocument();
  });
});

describe("the family shares with a doctor on Nabz", () => {
  const grant: Grant = { id: "g1", clinician_name: "Dr. Anjali Rath", registration_no: "OCMR 40213",
    council: "Odisha Council of Medical Registration", specialty: "General medicine", created_at: "2026-10-02T10:00:00Z",
    revoked: false, notes: 1 };
  const insights = () => ({
    report: { id: "r1", status: "explained", lab_name: "Anvaya Diagnostics", collected_at: "2026-08-19",
      created_at: "2026-08-20T10:00:00Z", rows: 1, note: null },
    person: { id: "p1", display_name: "Ramesh", sex: "male", age: 58 },
    analysed: true, critical: [], organs: [], explanation: null,
  });

  it("shares by email, explains a refusal, shows the doctor's note and withdraws", async () => {
    let grants: Grant[] = [];
    const calls = mockApi({
      "GET /v1/reports/r1/insights": insights,
      "GET /v1/reports/r1/explanation?lang=en": () => ({ state: "none", explanation: null }),
      "GET /v1/reports/r1/shares": () => [],
      "GET /v1/reports/r1/notes": () => [note("Please repeat the HbA1c test in three months.")],
      "GET /v1/reports/r1/grants": () => grants,
      "POST /v1/reports/r1/grants": (_, init) => {
        if (JSON.parse(String(init.body)).email !== "anjali@example.com") {
          return problem(404, { detail: "No.", code: "no_clinician" });
        }
        grants = [grant];
        return grant;
      },
      "DELETE /v1/grants/g1": () => {
        grants = [{ ...grant, revoked: true }];
        return undefined;
      },
    });
    renderRoute("/r/r1");
    // the doctor's note is beside the report
    expect(await screen.findByRole("heading", { name: "Doctor's note" })).toBeInTheDocument();
    expect(screen.getByText("Please repeat the HbA1c test in three months.")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Share with a doctor" }));
    const dialog = screen.getByRole("dialog", { name: "Share this report with a doctor" });
    const email = within(dialog).getByLabelText("The doctor's email");
    await userEvent.type(email, "someone@example.com");
    await userEvent.click(within(dialog).getByRole("button", { name: "Share" }));
    expect(await within(dialog).findByText(/no checked doctor on Nabz with that email/)).toBeInTheDocument();

    await userEvent.clear(email);
    await userEvent.type(email, "anjali@example.com");
    await userEvent.click(within(dialog).getByRole("button", { name: "Share" }));
    expect(await within(dialog).findByText("Dr. Anjali Rath")).toBeInTheDocument();
    expect(within(dialog).getByText(/OCMR 40213/)).toBeInTheDocument();
    expect(within(dialog).getByText("1 note")).toBeInTheDocument();

    await userEvent.click(within(dialog).getByRole("button", { name: "Withdraw" }));
    await waitFor(() => expect(calls.some((c) => c.method === "DELETE" && c.url === "/v1/grants/g1")).toBe(true));
    await waitFor(() => expect(within(dialog).queryByText("Dr. Anjali Rath")).not.toBeInTheDocument());
  });
});

describe("checking a doctor's registration", () => {
  it("lets an admin mark a registration as checked", async () => {
    let verified: string | null = null;
    const calls = mockApi({
      "GET /v1/auth/me": () => ADMIN,
      "GET /v1/admin/overview": () => ({}),
      "GET /v1/admin/clinicians": () => [{ ...REG, user_id: "d1", email: "anjali@example.com", verified_at: verified }],
      "POST /v1/admin/clinicians/d1/verify": () => {
        verified = "2026-10-03T10:00:00Z";
        return { ...REG, user_id: "d1", email: "anjali@example.com", verified_at: verified };
      },
    });
    renderRoute("/admin?tab=doctors");
    const row = (await screen.findByText("Dr. Anjali Rath")).closest("tr") as HTMLElement;
    expect(within(row).getByText("waiting")).toBeInTheDocument();
    await userEvent.click(within(row).getByRole("button", { name: "Mark as checked" }));
    await waitFor(() => expect(calls.find((c) => c.method === "POST")?.body).toEqual({ verified: true }));
    expect(await within(row).findByText("checked 3 Oct 2026")).toBeInTheDocument();
    expect(within(row).getByRole("button", { name: "Withdraw the check" })).toBeInTheDocument();
  });
});
