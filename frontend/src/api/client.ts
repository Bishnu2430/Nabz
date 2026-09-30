/** Thin fetch wrapper. Errors arrive as RFC 9457 problem details and become ApiError. */

export class ApiError extends Error {
  status: number;
  body: Record<string, unknown>;

  constructor(status: number, body: Record<string, unknown>) {
    super(typeof body.detail === "string" ? body.detail : `Request failed (${status})`);
    this.status = status;
    this.body = body;
  }

  /** The machine-readable reason, e.g. "invalid", "locked", "totp_required" (docs/12 §3). */
  get code(): string | undefined {
    return typeof this.body.code === "string" ? this.body.code : undefined;
  }
}

// The session cookie is HttpOnly; the CSRF token comes from /v1/auth/me or /login and goes on every unsafe request.
let csrfToken: string | undefined;
export const setCsrfToken = (token: string | undefined) => {
  csrfToken = token;
};
export const CSRF_HEADER = "X-CSRF-Token";

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const unsafe = (init.method ?? "GET") !== "GET";
  const headers: Record<string, string> = init.body instanceof FormData ? {} : { "Content-Type": "application/json" };
  if (unsafe && csrfToken) headers[CSRF_HEADER] = csrfToken;
  const res = await fetch(path, { credentials: "same-origin", ...init, headers: { ...headers, ...init.headers } });
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  const body = text ? JSON.parse(text) : {};
  if (!res.ok) throw new ApiError(res.status, body);
  return body as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body instanceof FormData ? body : JSON.stringify(body ?? {}) }),
  patch: <T>(path: string, body: unknown) => request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) => request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  delete: (path: string, body?: unknown) =>
    request<void>(path, { method: "DELETE", body: body === undefined ? undefined : JSON.stringify(body) }),
};
