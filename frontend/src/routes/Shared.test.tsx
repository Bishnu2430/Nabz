import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { Result, ShareLink } from "../api/types";
import { mockApi, problem, renderRoute, signedOut } from "../test/utils";

const creatinine: Result = {
  observation_id: "o1", report_id: "r1", date: "2026-07-04", test_code: "creatinine", test_name: "Creatinine",
  short_name: "Creat", organ: "kidney", value: "1.6", unit: "mg/dL", decimals: 2, ref_low: "0.7", ref_high: "1.3",
  ref_source: "report", status: "high", critical: false, flag_disagrees: false,
  previous: { value: 1.2, date: "2025-06-04", report_id: "r0" },
  change: { fraction: 0.333, direction: "up", significant: true, rcv_down: -0.13, rcv_up: 0.15 }, trend: null, percentile: null,
};
const link = (over: Partial<ShareLink> = {}): ShareLink => ({ id: "s1", label: "Dr. Nayak", created_at: "2026-07-05T10:00:00Z",
  expires_at: "2026-07-12T10:00:00Z", revoked: false, active: true, views: 0, last_viewed_at: null, ...over });

describe("sharing with a doctor", () => {
  it("creates a link with a QR code, shows it once, and withdraws it", async () => {
    let links: ShareLink[] = [];
    const calls = mockApi({
      "GET /v1/reports/r1/insights": () => ({
        report: { id: "r1", status: "explained", lab_name: "Anvaya Diagnostics", collected_at: "2026-07-04",
          created_at: "2026-07-05T10:00:00Z", rows: 1, note: null },
        person: { id: "p1", display_name: "Ramesh", sex: "male", age: 58 },
        analysed: true, critical: [], organs: [], explanation: null,
      }),
      "GET /v1/reports/r1/explanation?lang=en": () => ({ state: "none", explanation: null }),
      "GET /v1/reports/r1/shares": () => links,
      "POST /v1/reports/r1/shares": () => {
        links = [link()];
        return { ...link(), url: "http://localhost:5173/s/tok123", qr_svg: "data:image/svg+xml;base64,PHN2Zy8+" };
      },
      "DELETE /v1/shares/s1": () => {
        links = [link({ revoked: true, active: false })];
        return undefined;
      },
    });
    renderRoute("/r/r1");
    await userEvent.click(await screen.findByRole("button", { name: "Share with a doctor" }));
    const dialog = screen.getByRole("dialog", { name: "Share this report with a doctor" });
    await userEvent.type(within(dialog).getByLabelText(/Who is it for/), "Dr. Nayak");
    await userEvent.click(within(dialog).getByRole("button", { name: "Create the link" }));

    expect(await within(dialog).findByRole("img", { name: "QR code for the share link" })).toBeInTheDocument();
    expect(within(dialog).getByLabelText("Share link")).toHaveValue("http://localhost:5173/s/tok123");
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({ days: 7, label: "Dr. Nayak" });
    expect(within(dialog).getByText(/shown only once/)).toBeInTheDocument();

    await userEvent.click(await within(dialog).findByRole("button", { name: "Withdraw" }));
    await waitFor(() => expect(calls.some((c) => c.method === "DELETE")).toBe(true));
    expect(await within(dialog).findByText("withdrawn")).toBeInTheDocument();
  });

  it("shows the doctor one report without an account, with exact values", async () => {
    mockApi({
      "GET /v1/auth/me": signedOut,
      "GET /v1/shared/tok123": () => ({
        person: { display_name: "Ramesh Mohanty", sex: "male", age: 58 }, lab_name: "Anvaya Diagnostics",
        collected_at: "2026-07-04", note: "Not fasting", critical: [],
        organs: [{ code: "kidney", names: { en: "Kidneys" }, status: "high", results: [creatinine] }],
        questions: ["Should the test be repeated?"], expires_at: "2026-07-12T10:00:00Z",
      }),
    });
    renderRoute("/s/tok123");
    expect(await screen.findByRole("heading", { name: "Ramesh Mohanty" })).toBeInTheDocument();
    expect(screen.getByText(/Read-only; this link works until 12 Jul 2026/)).toBeInTheDocument();
    expect(screen.getByText("1.60 mg/dL")).toBeInTheDocument();
    expect(screen.getByText(/23 % above the upper limit 1.3/)).toHaveTextContent("+33 % since 4 Jun 2025");
    expect(screen.getByText("Should the test be repeated?")).toBeInTheDocument();
    expect(screen.getByText(/“Not fasting”/)).toBeInTheDocument();
  });

  it("says plainly when a link has expired or was withdrawn", async () => {
    mockApi({ "GET /v1/auth/me": signedOut, "GET /v1/shared/old": () => problem(404, { detail: "gone" }) });
    renderRoute("/s/old");
    expect(await screen.findByRole("heading", { name: "This link no longer works" })).toBeInTheDocument();
  });
});
