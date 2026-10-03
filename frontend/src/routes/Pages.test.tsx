import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import i18n from "../i18n";
import { mockApi, renderRoute, signedOut } from "../test/utils";

describe("the pages anyone can read", () => {
  it("answers common questions, one at a time", async () => {
    mockApi({ "GET /v1/auth/me": signedOut });
    renderRoute("/help");
    expect(await screen.findByRole("heading", { name: "Help" })).toBeInTheDocument();
    const question = screen.getByText("Where does the range come from?");
    const answer = screen.getByText(/From your lab's report/);
    expect(answer).not.toBeVisible();
    await userEvent.click(question);
    expect(answer).toBeVisible();
  });

  it("lists every source with its licence, and the LOINC notice", async () => {
    mockApi({ "GET /v1/auth/me": signedOut });
    renderRoute("/about");
    expect(await screen.findByRole("heading", { name: "About Nabz" })).toBeInTheDocument();
    const sources = screen.getByRole("heading", { name: "Sources and licences" }).closest("section") as HTMLElement;
    expect(within(sources).getByRole("link", { name: /MedlinePlus, U.S. National Library of Medicine/ })).toHaveAttribute("href", "https://medlineplus.gov/");
    expect(within(sources).getByText(/LOINC is copyright © Regenstrief Institute/)).toBeInTheDocument();
    expect(screen.getByText(/James Heilman, MD · CC BY-SA 4.0/)).toBeInTheDocument();
  });

  it("has terms of use in every language, linked from the footer and from sign-up", async () => {
    mockApi({ "GET /v1/auth/me": signedOut });
    renderRoute("/signup");
    const consent = await screen.findByText(/By creating an account you accept the/);
    expect(within(consent).getByRole("link", { name: "terms of use" })).toHaveAttribute("href", "/terms");
    expect(within(consent).getByRole("link", { name: "privacy notice" })).toHaveAttribute("href", "/privacy");

    const footer = screen.getByRole("navigation", { name: "More about Nabz" });
    await userEvent.click(within(footer).getByRole("link", { name: "Terms of use" }));
    expect(await screen.findByRole("heading", { name: "For doctors" })).toBeInTheDocument();

    await i18n.changeLanguage("or");
    expect(await screen.findByRole("heading", { name: "ବ୍ୟବହାର ସର୍ତ୍ତାବଳୀ" })).toBeInTheDocument();
    await i18n.changeLanguage("en");
  });
});
