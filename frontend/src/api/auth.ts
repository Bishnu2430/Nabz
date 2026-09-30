import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import i18n from "../i18n";
import { api, ApiError, setCsrfToken } from "./client";
import type { Lang } from "./types";

export type Role = "user" | "clinician" | "reviewer" | "admin";

export interface Me {
  id: string;
  email: string;
  role: Role;
  preferred_language: Lang;
  email_verified: boolean;
  totp_enabled: boolean;
  /** Staff must turn on two-step sign-in before anything else. */
  totp_required: boolean;
  csrf_token: string;
}

export interface TotpSetup {
  secret: string;
  uri: string;
  qr_svg: string;
}

type Message = { detail: string };

export const ME = ["me"] as const;

/** The signed-in account, or null when signed out. Keeps the CSRF token current. */
export function useMe() {
  return useQuery({
    queryKey: ME,
    queryFn: async () => {
      try {
        const me = await api.get<Me>("/v1/auth/me");
        setCsrfToken(me.csrf_token);
        return me;
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) {
          setCsrfToken(undefined);
          return null;
        }
        throw e;
      }
    },
    staleTime: 5 * 60_000,
  });
}

/** Store a fresh account answer (after sign-in or a change) without refetching. */
function useStoreMe() {
  const qc = useQueryClient();
  return (me: Me) => {
    setCsrfToken(me.csrf_token);
    qc.setQueryData(ME, me);
  };
}

export function useLogin() {
  const store = useStoreMe();
  return useMutation({
    mutationFn: (body: { email: string; password: string; totp_code?: string }) => api.post<Me>("/v1/auth/login", body),
    onSuccess: (me) => {
      store(me);
      if (i18n.resolvedLanguage !== me.preferred_language) void i18n.changeLanguage(me.preferred_language);
    },
  });
}

export const useRegister = () =>
  useMutation({
    mutationFn: (body: { email: string; password: string; preferred_language: Lang }) =>
      api.post<Message>("/v1/auth/register", body),
  });

export function useVerifyEmail() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (token: string) => api.post<Message>("/v1/auth/verify-email", { token }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ME }),
  });
}

export const useResendVerification = () =>
  useMutation({ mutationFn: () => api.post<Message>("/v1/auth/resend-verification") });

export const useForgotPassword = () =>
  useMutation({ mutationFn: (email: string) => api.post<Message>("/v1/auth/forgot-password", { email }) });

export const useResetPassword = () =>
  useMutation({
    mutationFn: (body: { token: string; password: string }) => api.post<Message>("/v1/auth/reset-password", body),
  });

export const useChangePassword = () =>
  useMutation({
    mutationFn: (body: { current_password: string; new_password: string }) =>
      api.post<Message>("/v1/auth/change-password", body),
  });

/** Sign out here, or everywhere; either way every cached answer belongs to the old session. */
export function useLogout(everywhere = false) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<void>(everywhere ? "/v1/auth/logout-all" : "/v1/auth/logout"),
    onSettled: () => {
      setCsrfToken(undefined);
      qc.clear();
      qc.setQueryData(ME, null);
    },
  });
}

export function useUpdateLanguage() {
  const store = useStoreMe();
  return useMutation({
    mutationFn: (preferred_language: Lang) => api.patch<Me>("/v1/auth/me", { preferred_language }),
    onSuccess: store,
  });
}

export const useTotpSetup = () => useMutation({ mutationFn: () => api.post<TotpSetup>("/v1/auth/totp/setup") });

export function useTotpEnable() {
  const store = useStoreMe();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (code: string) => api.post<Me>("/v1/auth/totp/enable", { code }),
    onSuccess: (me) => {
      store(me);
      // staff were blocked until now; anything that failed with 403 can load
      void qc.invalidateQueries({ predicate: (q) => q.queryKey[0] !== ME[0] });
    },
  });
}

export function useTotpDisable() {
  const store = useStoreMe();
  return useMutation({
    mutationFn: (password: string) => api.post<Me>("/v1/auth/totp/disable", { password }),
    onSuccess: store,
  });
}

export function useDeleteAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (password: string) => api.delete("/v1/auth/account", { password }),
    onSuccess: () => {
      setCsrfToken(undefined);
      qc.clear();
      qc.setQueryData(ME, null);
    },
  });
}

/** Only same-site paths are followed after sign-in, never "//evil.example" or a full URL. */
export function safeNext(next: string | null): string {
  return next && next.startsWith("/") && !next.startsWith("//") && !next.startsWith("/\\") ? next : "/home";
}
