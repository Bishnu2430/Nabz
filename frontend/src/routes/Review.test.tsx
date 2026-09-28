import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { Observation, Report } from "../api/types";
import { mockApi, renderRoute } from "../test/utils";

const base: Omit<Observation, "id" | "raw_name" | "test_code" | "test_name" | "confidence" | "needs_attention"> = {
  raw_value: "14.2", raw_unit: "g/dL", raw_range: "13.0 - 17.0", raw_flag: null, section: "Haematology",
  value: "14.2", unit: "g/dL", ref_low: "13.0", ref_high: "17.0", ref_source: "report",
  match_method: "exact", candidates: [], bbox: null, edited: false,
};

const rows: Observation[] = [
  { ...base, id: "a", raw_name: "Haemoglobin", test_code: "HGB", test_name: "Haemoglobin", confidence: 0.97, needs_attention: false },
  {
    ...base, id: "b", raw_name: "S. Creatnine", test_code: null, test_name: null, confidence: 0.2, needs_attention: true,
    raw_value: "1.1", value: null, unit: null, raw_unit: "mg/dL", match_method: "none",
    candidates: [["CREAT", "Creatinine", 0.82], ["CRP", "C-reactive protein", 0.41]],
  },
  { ...base, id: "c", raw_name: "Platelet count", test_code: "PLT", test_name: "Platelet count", confidence: 0.55, needs_attention: true },
];

const report = (over: Partial<Report> = {}): Report => ({
  id: "r1", profile_id: "p1", status: "needs_review", lab_name: "Anvaya Diagnostics", collected_at: "2026-09-01",
  created_at: "2026-09-02T10:00:00Z", pages: [{ page_no: 0, width: 595, height: 842, source: "text-layer", quality: null }],
  observations: rows, needs_attention: 2, unmapped: 1, confidence_threshold: 0.8, ...over,
});

const catalogue = [
  { code: "CREAT", name: "Creatinine", short_name: "Creat", panel: "KFT", unit: "mg/dL", organ: "kidney" },
  { code: "HGB", name: "Haemoglobin", short_name: "Hb", panel: "CBC", unit: "g/dL", organ: "blood" },
];

describe("Review", () => {
  it("lists the weakest rows first and blocks confirming while a row has no test", async () => {
    mockApi({ "GET /v1/reports/r1": () => report(), "GET /v1/catalogue/tests": () => catalogue });
    renderRoute("/r/r1/review");

    const items = await screen.findAllByRole("listitem");
    const names = items.map((li) => within(li).getByRole("heading", { level: 3 }).textContent);
    expect(names).toEqual(["Choose a test", "Platelet count", "Haemoglobin"]);

    expect(screen.getByText("2 values need a look")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirm values" })).toBeDisabled();
    expect(screen.getByText(/Every row needs a test and a number/)).toBeInTheDocument();
  });

  it("maps an unmatched row when a suggestion is picked", async () => {
    const calls = mockApi({
      "GET /v1/reports/r1": () => report(),
      "GET /v1/catalogue/tests": () => catalogue,
      "PATCH /v1/observations/b": () => ({ ...rows[1], test_code: "CREAT", test_name: "Creatinine" }),
    });
    renderRoute("/r/r1/review");

    await userEvent.click(await screen.findByRole("button", { name: "Creatinine" }));
    await waitFor(() => expect(calls.some((c) => c.method === "PATCH")).toBe(true));
    expect(calls.find((c) => c.method === "PATCH")?.body).toEqual({ test_code: "CREAT" });
  });

  it("confirms, then shows the seal and stops editing", async () => {
    let status: Report["status"] = "needs_review";
    const mapped = rows.map((r) => ({ ...r, test_code: r.test_code ?? "CREAT", test_name: r.test_name ?? "Creatinine" }));
    const calls = mockApi({
      "GET /v1/reports/r1": () => report({ status, observations: mapped, unmapped: 0, needs_attention: 1 }),
      "GET /v1/catalogue/tests": () => catalogue,
      "POST /v1/reports/r1/confirm": () => {
        status = "verified";
        return { report_id: "r1", status };
      },
    });
    renderRoute("/r/r1/review");

    await userEvent.click(await screen.findByRole("button", { name: "Confirm values" }));
    expect(await screen.findByText("Values confirmed")).toBeInTheDocument();
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({});
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
  });

  it("shows the ensō while the report is still being read", async () => {
    mockApi({ "GET /v1/reports/r1": () => report({ status: "processing", observations: [] }) });
    renderRoute("/r/r1/review");
    const status = await screen.findByText("Reading the report…");
    expect(status.closest("[role=status]")).not.toBeNull();
  });
});
