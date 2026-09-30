import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { safeNext } from "../../api/auth";
import { ME, mockApi, problem, renderRoute, signedOut } from "../../test/utils";

describe("sign-in guard", () => {
  it("sends signed-out visitors to sign-in and back to where they were going", async () => {
    let signedIn = false;
    const calls = mockApi({
      "GET /v1/auth/me": () => (signedIn ? ME : signedOut()),
      "POST /v1/auth/login": () => {
        signedIn = true;
        return ME;
      },
      "GET /v1/profiles": () => [],
    });
    const { router } = renderRoute("/home");

    await userEvent.type(await screen.findByLabelText("Email"), "asha@example.com");
    expect(router.state.location.pathname).toBe("/login");
    await userEvent.type(screen.getByLabelText("Password"), "correct horse battery");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("heading", { name: "Add the first person" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/home");
    expect(calls.find((c) => c.url === "/v1/auth/login")?.body).toEqual({
      email: "asha@example.com", password: "correct horse battery",
    });
  });

  it("asks for the authenticator code when the account has two-step sign-in", async () => {
    const calls = mockApi({
      "GET /v1/auth/me": signedOut,
      "POST /v1/auth/login": (_, init) =>
        JSON.parse(String(init.body)).totp_code
          ? problem(401, { detail: "no", code: "totp_invalid" })
          : problem(401, { detail: "code please", code: "totp_required" }),
    });
    renderRoute("/login");
    await userEvent.type(await screen.findByLabelText("Email"), "asha@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "correct horse battery");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await userEvent.type(await screen.findByLabelText("6-digit code"), "123 456");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("That code didn't work");
    expect(calls.filter((c) => c.url === "/v1/auth/login").at(-1)?.body).toMatchObject({ totp_code: "123456" });
  });

  it("sends staff without two-step sign-in to set it up", async () => {
    mockApi({
      "GET /v1/auth/me": () => ({ ...ME, role: "admin", totp_required: true }),
      "GET /v1/profiles": () => [],
    });
    const { router } = renderRoute("/home");
    expect(await screen.findByText(/Staff accounts need two-step sign-in/)).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/settings");
    expect(screen.queryByRole("link", { name: "Family" })).not.toBeInTheDocument();
  });

  it("only follows same-site paths after sign-in", () => {
    expect(safeNext("/r/abc")).toBe("/r/abc");
    expect(safeNext("//evil.example")).toBe("/home");
    expect(safeNext("https://evil.example")).toBe("/home");
    expect(safeNext("/\\evil.example")).toBe("/home");
    expect(safeNext(null)).toBe("/home");
  });
});

describe("sign-up", () => {
  it("explains a weak password in the reader's language before sending anything", async () => {
    const calls = mockApi({ "GET /v1/auth/me": signedOut, "POST /v1/auth/register": () => ({ detail: "sent" }) });
    renderRoute("/signup");
    await userEvent.type(await screen.findByLabelText("Email"), "asha@example.com");
    await userEvent.type(screen.getByLabelText("New password"), "short");
    await userEvent.click(screen.getByRole("button", { name: "Create account" }));
    expect(screen.getByText("Use at least 10 characters.")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "POST")).toBe(false);

    await userEvent.type(screen.getByLabelText("New password"), " and some more words");
    await userEvent.click(screen.getByRole("button", { name: "Create account" }));
    expect(await screen.findByRole("heading", { name: "Check your email" })).toBeInTheDocument();
    expect(calls.find((c) => c.method === "POST")?.body).toMatchObject({ preferred_language: "en" });
  });
});

describe("email and password links", () => {
  it("confirms the email only when the button is pressed", async () => {
    const calls = mockApi({ "GET /v1/auth/me": signedOut, "POST /v1/auth/verify-email": () => ({ detail: "ok" }) });
    renderRoute("/verify-email?token=abc");
    const button = await screen.findByRole("button", { name: "Confirm my email" });
    expect(calls.some((c) => c.method === "POST")).toBe(false);
    await userEvent.click(button);
    expect(await screen.findByRole("heading", { name: "Email confirmed" })).toBeInTheDocument();
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({ token: "abc" });
  });

  it("says when a reset link has expired", async () => {
    mockApi({
      "GET /v1/auth/me": signedOut,
      "POST /v1/auth/reset-password": () => problem(400, { detail: "x", code: "token" }),
    });
    renderRoute("/reset-password?token=old");
    await userEvent.type(await screen.findByLabelText("New password"), "a brand new passphrase");
    await userEvent.type(screen.getByLabelText("New password again"), "a brand new passphrase");
    await userEvent.click(screen.getByRole("button", { name: "Change password" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("This link has expired");
  });
});

describe("settings", () => {
  it("sends the CSRF token on changes and shows the QR code for two-step sign-in", async () => {
    const calls = mockApi({
      "GET /v1/profiles": () => [],
      "POST /v1/auth/totp/setup": () => ({ secret: "ABCDEFGHIJKLMNOP", uri: "otpauth://totp/Nabz:a", qr_svg: "data:image/svg+xml;base64,PHN2Zy8+" }),
      "POST /v1/auth/totp/enable": () => ({ ...ME, totp_enabled: true }),
    });
    renderRoute("/settings");
    await userEvent.click(await screen.findByRole("button", { name: "Set up two-step sign-in" }));
    expect(await screen.findByRole("img", { name: "QR code for your authenticator app" })).toBeInTheDocument();
    expect(screen.getByText("ABCD EFGH IJKL MNOP")).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText("6-digit code"), "123456");
    await userEvent.click(screen.getByRole("button", { name: "Turn on" }));
    expect(await screen.findByText("Two-step sign-in is on.")).toBeInTheDocument();
    const enable = calls.find((c) => c.url === "/v1/auth/totp/enable");
    expect(enable?.headers["X-CSRF-Token"]).toBe("csrf-1");
  });

  it("deletes a person only after their name is typed", async () => {
    const calls = mockApi({
      "GET /v1/profiles": () => [{ id: "p1", display_name: "Asha", sex: "female", date_of_birth: null,
        relationship: "self", preferred_language: "en", reports: 2, latest_report_at: null }],
      "DELETE /v1/profiles/p1": () => undefined,
    });
    renderRoute("/settings");
    await userEvent.click(await screen.findByRole("button", { name: "Delete" }));
    const confirm = screen.getByRole("button", { name: "Delete for good" });
    expect(confirm).toBeDisabled();
    await userEvent.type(screen.getByLabelText("Type Asha to confirm"), "Asha");
    await userEvent.click(confirm);
    await waitFor(() => expect(calls.some((c) => c.method === "DELETE")).toBe(true));
    expect(screen.getByRole("link", { name: "Download data" })).toHaveAttribute("href", "/v1/profiles/p1/export");
  });
});
