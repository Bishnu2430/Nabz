import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { vi } from "vitest";

import { routes } from "../routes";

type Handler = (url: string, init: RequestInit) => unknown | Response;

/** Stub fetch with a map of "METHOD /path" -> handler. Unmatched calls fail the test loudly. */
export function mockApi(handlers: Record<string, Handler>) {
  const calls: { method: string; url: string; body: unknown }[] = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const url = String(input);
    const method = (init.method ?? "GET").toUpperCase();
    const body = typeof init.body === "string" ? JSON.parse(init.body) : init.body;
    calls.push({ method, url, body });
    const handler = handlers[`${method} ${url}`];
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

export function renderRoute(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  return render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}
