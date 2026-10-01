import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { BodyMapFrame, ResultBrief } from "../api/types";
import { mockApi, renderRoute } from "../test/utils";

const brief = (over: Partial<ResultBrief>): ResultBrief => ({
  test_code: "hba1c", test_name: "HbA1c", short_name: "HbA1c", value: "7.6", unit: "%", decimals: 1, status: "high",
  ref_low: "4.0", ref_high: "5.6", date: "2025-08-20", report_id: "r1", ...over });

const person = {
  id: "p1", display_name: "Ramesh Mohanty", sex: "male", date_of_birth: "1968-03-14", relationship: "spouse",
  preferred_language: "en", reports: 2, latest_report_at: "2025-08-21T10:00:00Z", last_tested: "2025-08-20",
  attention: [brief({})],
};

const frames: BodyMapFrame[] = [
  { report_id: "r0", date: "2024-06-05", lab_name: "Mahanadi Clinical Laboratory", organs: [
    { code: "pancreas", status: "high", out_of_range: 1, results: 1, tests: [brief({ value: "7.3", date: "2024-06-05", report_id: "r0" })] },
    { code: "bone", status: "low", out_of_range: 1, results: 1, tests: [brief({ test_code: "vitamin_d", test_name: "Vitamin D",
      short_name: "Vit D", value: "16", unit: "ng/mL", status: "low", ref_low: "30", ref_high: "100", date: "2024-06-05",
      report_id: "r0" })] }] },
  { report_id: "r1", date: "2025-08-20", lab_name: "Anvaya Diagnostics", organs: [
    { code: "pancreas", status: "high", out_of_range: 1, results: 1, tests: [brief({})] },
    { code: "bone", status: "normal", out_of_range: 0, results: 1, tests: [brief({ test_code: "vitamin_d",
      test_name: "Vitamin D", short_name: "Vit D", value: "31", unit: "ng/mL", status: "normal", ref_low: "30",
      ref_high: "100" })] }] },
];

describe("exact values across the family", () => {
  it("puts each person's out-of-range values and last test date on their card", async () => {
    mockApi({ "GET /v1/profiles": () => [person] });
    renderRoute("/home");
    expect(await screen.findByText(/last tested 20 Aug 2025/)).toBeInTheDocument();
    expect(screen.getByText("1 result outside its range now")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "HbA1c 7.6 %, 36 % above the upper limit 5.6" }))
      .toHaveAttribute("href", "/p/p1/tests/hba1c");
  });

  it("lists every test with its latest value and finds one by name", async () => {
    mockApi({ "GET /v1/profiles": () => [person], "GET /v1/profiles/p1/body-map": () => frames });
    renderRoute("/p/p1/tests");
    expect(await screen.findByText("2 tests, each with its latest value and its history.")).toBeInTheDocument();
    expect(screen.getByText("36 % above the upper limit 5.6")).toBeInTheDocument();
    await userEvent.type(screen.getByPlaceholderText(/Search tests/), "vitamin");
    expect(screen.queryByText("HbA1c")).not.toBeInTheDocument();
    expect(screen.getByText("within 30 – 100")).toBeInTheDocument();
  });

  it("compares two reports and says what came back into range", async () => {
    mockApi({ "GET /v1/profiles": () => [person], "GET /v1/profiles/p1/body-map": () => frames });
    renderRoute("/p/p1/compare");
    expect(await screen.findByText("1 test moved into or out of its range between these reports.")).toBeInTheDocument();
    const row = screen.getByRole("link", { name: "Vitamin D" }).closest("tr")!;
    expect(within(row).getByText("+94 %")).toBeInTheDocument();
    expect(within(row).getByText("back in range")).toBeInTheDocument();
  });
});

describe("other records", () => {
  it("stores an X-ray report with its details and lists it", async () => {
    let saved = false;
    // a person with a report shows the records section
    const calls = mockApi({
      "GET /v1/profiles": () => [person],
      "GET /v1/profiles/p1/reports": () => [{ id: "r1", status: "explained", lab_name: null, collected_at: "2025-08-20",
        created_at: "2025-08-20T10:00:00Z", rows: 3, note: null, out_of_range: [] }],
      "GET /v1/profiles/p1/body-map": () => [],
      "GET /v1/profiles/p1/watch": () => [],
      "GET /v1/profiles/p1/consents": () => [],
      "GET /v1/profiles/p1/records": () => (saved ? [{ id: "x1", profile_id: "p1", kind: "imaging",
        title: "Chest X-ray", record_date: "2024-06-05", facility: "Utkal Imaging", notes: null,
        mime_type: "application/pdf", size_bytes: 604000, created_at: "2024-06-05T10:00:00Z" }] : []),
      "POST /v1/profiles/p1/records": () => {
        saved = true;
        return { id: "x1" };
      },
    });
    renderRoute("/p/p1");
    await userEvent.click(await screen.findByRole("button", { name: "Add a record" }));
    await userEvent.upload(screen.getByLabelText(/^File/), new File(["%PDF-1.4"], "chest.pdf", { type: "application/pdf" }));
    await userEvent.type(screen.getByLabelText("Name"), "Chest X-ray");
    await userEvent.click(screen.getByRole("button", { name: "Save record" }));
    await waitFor(() => expect(calls.some((c) => c.method === "POST")).toBe(true));
    const form = calls.find((c) => c.method === "POST")!.body as FormData;
    expect(form.get("kind")).toBe("imaging");
    expect(form.get("title")).toBe("Chest X-ray");
    expect(await screen.findByRole("heading", { name: "Chest X-ray" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open \(PDF, 590 KB\)/ })).toHaveAttribute("href", "/v1/records/x1/file");
  });
});

describe("report notes", () => {
  it("saves the family's own note on a report", async () => {
    const calls = mockApi({
      "GET /v1/reports/r1/insights": () => ({
        report: { id: "r1", status: "explained", lab_name: "Anvaya Diagnostics", collected_at: "2025-08-20",
          created_at: "2025-08-20T10:00:00Z", rows: 1, note: null },
        person: { id: "p1", display_name: "Ramesh Mohanty", sex: "male", age: 57 },
        analysed: true, critical: [], organs: [], explanation: null,
      }),
      "GET /v1/reports/r1/explanation?lang=en": () => ({ state: "none", explanation: null }),
      "PATCH /v1/reports/r1": () => ({ id: "r1", note: "Not fasting" }),
    });
    renderRoute("/r/r1");
    await userEvent.click(await screen.findByRole("button", { name: "Add a note" }));
    await userEvent.type(screen.getByLabelText("Your note"), "Not fasting");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(calls.find((c) => c.method === "PATCH")?.body).toEqual({ note: "Not fasting" }));
  });
});

describe("imaging viewer", () => {
  it("opens the study with the radiologist's words and responds to the keyboard", async () => {
    mockApi({
      "GET /v1/profiles": () => [person],
      "GET /v1/profiles/p1/reports": () => [{ id: "r1", status: "explained", lab_name: null, collected_at: "2025-08-20",
        created_at: "2025-08-20T10:00:00Z", rows: 3, note: null, out_of_range: [] }],
      "GET /v1/profiles/p1/body-map": () => [],
      "GET /v1/profiles/p1/watch": () => [],
      "GET /v1/profiles/p1/consents": () => [],
      "GET /v1/profiles/p1/records": () => [{ id: "x1", profile_id: "p1", kind: "imaging", title: "X-ray left knee",
        record_date: "2025-04-12", facility: "Utkal Imaging & Diagnostics", notes: null, mime_type: "application/pdf",
        size_bytes: 640000, created_at: "2025-04-12T10:00:00Z", has_image: true,
        study_title: "X-RAY LEFT KNEE (AP VIEW)", findings: ["Reduction of the joint space."],
        impression: ["Degenerative changes of the left knee."], image_credit: "Image: J. Author · CC BY-SA 4.0" }],
    });
    renderRoute("/p/p1");
    await userEvent.click(await screen.findByRole("button", { name: "View the image: X-ray left knee" }));
    const dialog = screen.getByRole("dialog", { name: "X-RAY LEFT KNEE (AP VIEW)" });
    expect(within(dialog).getByText("Reduction of the joint space.")).toBeInTheDocument();
    expect(within(dialog).getByText("Degenerative changes of the left knee.")).toBeInTheDocument();
    expect(within(dialog).getByText("Image: J. Author · CC BY-SA 4.0")).toBeInTheDocument();

    await userEvent.keyboard("i");
    expect(within(dialog).getByRole("button", { name: "Invert" })).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(within(dialog).getByRole("button", { name: "Magnifier" }));
    expect(within(dialog).getByText("Move over the image to magnify a spot.")).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});

describe("story mode", () => {
  it("steps through a person's reports with each turning point in words", async () => {
    mockApi({
      "GET /v1/profiles": () => [person],
      "GET /v1/profiles/p1/body-map": () => frames,
      "GET /v1/profiles/p1/records": () => [],
      "GET /v1/profiles/p1/reports": () => [{ id: "r1", status: "explained", lab_name: null, collected_at: "2025-08-20",
        created_at: "2025-08-20T10:00:00Z", rows: 2, note: "Walking daily since June", out_of_range: [] }],
    });
    renderRoute("/p/p1/story");
    expect(await screen.findByRole("heading", { name: "Ramesh Mohanty: the story so far" })).toBeInTheDocument();
    expect(screen.getByText("Chapter 1 of 2 · Mahanadi Clinical Laboratory")).toBeInTheDocument();
    expect(screen.getByText(/The first report on record: 2 results, 2 outside their range/)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Next chapter" }));
    expect(screen.getByRole("heading", { name: "20 Aug 2025" })).toBeInTheDocument();
    expect(screen.getByText("Vitamin D came back into range: 31.0 ng/mL (it was 16.0 ng/mL).")).toBeInTheDocument();
    expect(screen.getByText(/HbA1c reached its highest so far|HbA1c moved further from its range: 7.3 % to 7.6 %/)).toBeInTheDocument();
    expect(screen.getByText("The family's note: “Walking daily since June”")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Play again" })).toBeInTheDocument();
  });
});
