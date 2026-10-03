import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { CatalogueTest, CriticalLimit, KbDocument, LimitForReview } from "../../api/catalogue";
import { ME, mockApi, problem, renderRoute } from "../../test/utils";

const ADMIN = { ...ME, id: "a1", role: "admin", totp_enabled: true };
const REVIEWER = { ...ME, id: "r1", role: "reviewer", totp_enabled: true };

const limit = (over: Partial<CriticalLimit> = {}): CriticalLimit => ({ low: "2.8", high: "6.2", source: "Commonly published adult critical limits",
  reviewed_by: null, reviewed_at: null, proposed: null, ...over });
const potassium = (over: Partial<CatalogueTest> = {}): CatalogueTest => ({
  code: "potassium", loinc: "2823-3", name: "Potassium", short_name: "K", panel: "Electrolytes", organ: "kidney", unit: "mmol/L",
  decimals: 1, plausible_min: "1", plausible_max: "10", aliases: ["S. Potassium"], conversions: [],
  ranges: [{ sex: "unknown", age_min: 18, age_max: 120, low: "3.5", high: "5.1" }], critical: limit(), history: [], ...over,
});

describe("the catalogue on the console", () => {
  it("lists the tests and edits a test's aliases, refusing a name another test uses", async () => {
    let test = potassium();
    const calls = mockApi({
      "GET /v1/auth/me": () => ADMIN,
      "GET /v1/admin/catalogue": () => [{ code: "potassium", name: "Potassium", short_name: "K", organ: "kidney", unit: "mmol/L",
        aliases: test.aliases.length, conversions: 0, ranges: 1, critical: test.critical }],
      "GET /v1/admin/catalogue/potassium": () => test,
      "PATCH /v1/admin/catalogue/potassium": (_, init) => {
        const aliases = JSON.parse(String(init.body)).aliases as string[];
        if (aliases.includes("S. Creatinine")) return problem(409, { detail: "x", code: "alias_taken", alias: "S. Creatinine", test: "creatinine" });
        test = potassium({ aliases, history: [{ at: "2026-10-03T10:00:00Z", actor: "admin@nabz.local", action: "catalogue.test", meta: null }] });
        return test;
      },
    });
    renderRoute("/admin?tab=catalogue");
    const row = (await screen.findByRole("button", { name: "Potassium" })).closest("tr") as HTMLElement;
    expect(within(row).getByText("2.8 – 6.2 mmol/L")).toBeInTheDocument();
    expect(within(row).getByText("not yet signed off")).toBeInTheDocument();

    await userEvent.click(within(row).getByRole("button", { name: "Potassium" }));
    const dialog = await screen.findByRole("dialog", { name: "Potassium" });
    const aliases = within(dialog).getByRole("textbox", { name: "Aliases" });
    await userEvent.type(aliases, "\nS. Creatinine");
    const save = within(dialog).getAllByRole("button", { name: "Save" })[1];
    await userEvent.click(save);
    expect(await within(dialog).findByText("“S. Creatinine” already names another test (creatinine).")).toBeInTheDocument();

    await userEvent.clear(aliases);
    await userEvent.type(aliases, "S. Potassium\nSerum K");
    await userEvent.click(save);
    await waitFor(() => expect(calls.at(-2)?.body).toEqual({ aliases: ["S. Potassium", "Serum K"] }));
    expect(await within(dialog).findByText("Names, aliases or values changed")).toBeInTheDocument();
  });

  it("proposes a critical limit, which waits for clinical review", async () => {
    let test = potassium();
    const calls = mockApi({
      "GET /v1/auth/me": () => ADMIN,
      "GET /v1/admin/catalogue": () => [{ code: "potassium", name: "Potassium", short_name: "K", organ: "kidney", unit: "mmol/L",
        aliases: 1, conversions: 0, ranges: 1, critical: test.critical }],
      "GET /v1/admin/catalogue/potassium": () => test,
      "PUT /v1/admin/catalogue/potassium/critical-limit": (_, init) => {
        const body = JSON.parse(String(init.body));
        test = potassium({ critical: limit({ proposed: { low: body.low, high: body.high, at: "2026-10-03T10:00:00Z", by: "admin@nabz.local", note: body.note } }) });
        return test;
      },
    });
    renderRoute("/admin?tab=catalogue");
    await userEvent.click(await screen.findByRole("button", { name: "Potassium" }));
    const dialog = await screen.findByRole("dialog", { name: "Potassium" });
    const high = within(dialog).getByLabelText("Critically high above (mmol/L)");
    expect(high).toHaveValue("6.2");
    await userEvent.clear(high);
    await userEvent.type(high, "5.5");
    await userEvent.type(within(dialog).getByLabelText("Reason for the change"), "Hospital protocol");
    await userEvent.click(within(dialog).getByRole("button", { name: "Propose" }));

    await waitFor(() => expect(calls.find((c) => c.method === "PUT")?.body).toEqual({ low: "2.8", high: "5.5", note: "Hospital protocol" }));
    expect(await within(dialog).findByText(/Proposed: 2.8 – 5.5 mmol\/L, by admin@nabz.local on 3 Oct 2026/)).toBeInTheDocument();
    expect(within(dialog).getByText("change waiting for clinical review")).toBeInTheDocument();
    expect(within(dialog).getByText("2.8 – 6.2 mmol/L")).toBeInTheDocument(); // the current limits still apply
  });
});

describe("critical limits in clinical review", () => {
  it("shows a proposal beside the current limits and approves it", async () => {
    let item: LimitForReview = { code: "potassium", name: "Potassium", unit: "mmol/L",
      critical: limit({ proposed: { low: "2.8", high: "5.5", at: "2026-10-03T10:00:00Z", by: "admin@nabz.local", note: "Hospital protocol" } }),
      ranges: [{ sex: "unknown", age_min: 18, age_max: 120, low: "3.5", high: "5.1" }] };
    const calls = mockApi({
      "GET /v1/auth/me": () => REVIEWER,
      "GET /v1/review/summary": () => ({ explanations: {}, fallback_reasons: {}, blocked_rate: null, questions: {}, refusals: {},
        feedback: {}, open: { explanation: 0, question: 0, feedback: 0 }, reviewed: 0 }),
      "GET /v1/review/critical-limits": () => [item],
      "POST /v1/review/critical-limits/potassium": () => {
        item = { ...item, critical: limit({ high: "5.5", reviewed_by: "asha@example.com", reviewed_at: "2026-10-03" }) };
        return { critical: item.critical, results_changed: 2 };
      },
    });
    renderRoute("/review?tab=limits");
    expect(await screen.findByText("critically low below 2.8, high above 6.2 mmol/L")).toBeInTheDocument();
    expect(screen.getByText("critically low below 2.8, high above 5.5 mmol/L")).toBeInTheDocument();
    expect(screen.getByText(/Hospital protocol/)).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Critical limits\s*1/ })).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText("Your note (optional)"), "Agreed");
    await userEvent.click(screen.getByRole("button", { name: "Approve" }));
    await waitFor(() => expect(calls.find((c) => c.method === "POST")?.body).toEqual({ approve: true, note: "Agreed" }));
    expect(await screen.findByText("Approved. 2 results changed status and will be explained again.")).toBeInTheDocument();
    expect(await screen.findByText(/signed off by asha@example.com/)).toBeInTheDocument();
  });
});

describe("the knowledge base on the console", () => {
  it("adds a document for a test and says how many passages it made", async () => {
    let docs: KbDocument[] = [];
    const calls = mockApi({
      "GET /v1/auth/me": () => ADMIN,
      "GET /v1/admin/knowledge": () => ({ documents: docs, chunks: docs.length * 2, embedder: "intfloat/multilingual-e5-small (onnx int8)" }),
      "GET /v1/admin/catalogue": () => [{ code: "hba1c", name: "HbA1c", short_name: "HbA1c", organ: "pancreas", unit: "%", aliases: 0,
        conversions: 0, ranges: 1, critical: null }],
      "POST /v1/admin/knowledge": (_, init) => {
        const body = JSON.parse(String(init.body));
        docs = [{ id: "k1", title: body.title, source_org: body.source_org, url: body.url, license: body.license, language: "en",
          retrieved_at: "2026-10-03", chunks: 2, tests: ["hba1c"], citations: 0 }];
        return docs[0];
      },
    });
    renderRoute("/admin?tab=knowledge");
    expect(await screen.findByText("intfloat/multilingual-e5-small (onnx int8)")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Add a document" }));
    await userEvent.type(screen.getByLabelText("Title"), "Hemoglobin A1C (HbA1c) Test");
    await userEvent.type(screen.getByLabelText("Publisher"), "MedlinePlus");
    await userEvent.type(screen.getByLabelText("Address (URL)"), "https://medlineplus.gov/lab-tests/hemoglobin-a1c-hba1c-test/");
    await userEvent.selectOptions(screen.getByLabelText("The test it is about"), "hba1c");
    await userEvent.type(screen.getByLabelText("Text"), "The HbA1c test shows your average blood sugar over the past three months.");
    await userEvent.click(screen.getByRole("button", { name: "Add and embed" }));

    await waitFor(() => expect(calls.find((c) => c.method === "POST")?.body).toMatchObject({
      title: "Hemoglobin A1C (HbA1c) Test", license: "Public domain (U.S. government work)", test_code: "hba1c", language: "en" }));
    expect(await screen.findByText("Added as 2 passages")).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: /Hemoglobin A1C \(HbA1c\) Test/ })).toHaveAttribute("href",
      "https://medlineplus.gov/lab-tests/hemoglobin-a1c-hba1c-test/");
  });
});
