import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { mockApi, renderRoute } from "../test/utils";

describe("Home", () => {
  it("asks for consent before creating the first person", async () => {
    const calls = mockApi({
      "GET /v1/profiles": () => [],
      "POST /v1/profiles": () => ({
        id: "p1", display_name: "Asha", sex: "female", date_of_birth: null, relationship: "self",
        preferred_language: "en", reports: 0, latest_report_at: null,
      }),
    });
    renderRoute("/home");

    await userEvent.type(await screen.findByLabelText("Name"), "Asha");
    await userEvent.click(screen.getByRole("button", { name: "Add person" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Consent is needed");
    expect(calls.some((c) => c.method === "POST")).toBe(false);

    await userEvent.click(screen.getByLabelText(/I agree that Nabz may read/));
    await userEvent.click(screen.getByRole("button", { name: "Add person" }));
    await waitFor(() => expect(calls.some((c) => c.method === "POST")).toBe(true));
    expect(calls.find((c) => c.method === "POST")?.body).toMatchObject({ display_name: "Asha", consent_processing: true });
  });

  it("shows a card per person", async () => {
    mockApi({
      "GET /v1/profiles": () => [
        { id: "p1", display_name: "Asha", sex: "female", date_of_birth: null, relationship: "self",
          preferred_language: "en", reports: 2, latest_report_at: "2026-09-02T10:00:00Z" },
      ],
    });
    renderRoute("/home");
    expect(await screen.findByRole("heading", { name: "Asha" })).toBeInTheDocument();
    expect(screen.getByText(/2 reports/)).toBeInTheDocument();
  });
});
