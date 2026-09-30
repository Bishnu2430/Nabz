import { MutationCache, QueryCache, QueryClient } from "@tanstack/react-query";

import { ME } from "./auth";
import { ApiError, setCsrfToken } from "./client";

/**
 * One place for query defaults. A 401 anywhere means the session ended (idle expiry, signed out on another
 * device), so the account is cleared and the sign-in guard takes over.
 */
export function makeQueryClient(overrides: { retry?: false } = {}): QueryClient {
  const signedOut = (error: unknown) => {
    if (error instanceof ApiError && error.status === 401 && client.getQueryData(ME)) {
      setCsrfToken(undefined);
      client.setQueryData(ME, null);
    }
  };
  const client: QueryClient = new QueryClient({
    queryCache: new QueryCache({ onError: signedOut }),
    mutationCache: new MutationCache({ onError: signedOut }),
    defaultOptions: {
      queries: {
        staleTime: 15_000,
        // 4xx answers won't change on retry
        retry: overrides.retry ?? ((count, error) => !(error instanceof ApiError && error.status < 500) && count < 2),
      },
      mutations: { retry: false },
    },
  });
  return client;
}
