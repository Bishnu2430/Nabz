import { QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { vi } from "vitest";

import type { Me } from "../api/auth";
import { makeQueryClient } from "../api/queryClient";
import { routes } from "../routes";

type Handler = (url: string, init: RequestInit) => unknown | Response;

export const ME: Me = {
  id: "u1", email: "asha@example.com", role: "user", preferred_language: "en", email_verified: true,
  totp_enabled: false, totp_required: false, csrf_token: "csrf-1",
};

export const problem = (status: number, body: Record<string, unknown>) =>
  new Response(JSON.stringify({ status, ...body }), { status, headers: { "Content-Type": "application/json" } });

/**
 * Stub fetch with a map of "METHOD /path" -> handler. Unmatched calls fail the test loudly.
 * Signed in as ME unless the handlers answer "GET /v1/auth/me" themselves.
 */
export function mockApi(handlers: Record<string, Handler>) {
  const all: Record<string, Handler> = { "GET /v1/auth/me": () => ME, ...handlers };
  const calls: { method: string; url: string; body: unknown; headers: Record<string, string> }[] = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const url = String(input);
    const method = (init.method ?? "GET").toUpperCase();
    const body = typeof init.body === "string" ? JSON.parse(init.body) : init.body;
    calls.push({ method, url, body, headers: (init.headers ?? {}) as Record<string, string> });
    const handler = all[`${method} ${url}`];
    if (!handler) throw new Error(`Unexpected request: ${method} ${url}`);
    const result = handler(url, init);
    if (result instanceof Response) return result;
    return new Response(result === undefined ? null : JSON.stringify(result), {
      status: result === undefined ? 204 : 200,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return calls;
}

export const signedOut = () => problem(401, { detail: "Please sign in." });

export function renderRoute(path: string) {
  const client = makeQueryClient({ retry: false });
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  const view = render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return { ...view, router };
}
