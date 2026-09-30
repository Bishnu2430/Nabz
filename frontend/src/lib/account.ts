import { useTranslation } from "react-i18next";

import { ApiError } from "../api/client";

export const MIN_PASSWORD_LENGTH = 10;

/** Mirrors the server's check (backend/app/core/security.py) so people see the reason in their language. */
export function passwordProblem(password: string, email = ""): "too_short" | "repetitive" | "has_email" | null {
  if (password.length < MIN_PASSWORD_LENGTH) return "too_short";
  if (new Set(password).size < 4) return "repetitive";
  const local = email.split("@")[0]?.toLowerCase();
  if (local && password.toLowerCase().includes(local)) return "has_email";
  return null;
}

/** A translated message for an account error code ("invalid", "locked", …), else the server's own words. */
export function useAuthMessage() {
  const { t, i18n } = useTranslation();
  return (error: unknown): string => {
    if (error instanceof ApiError) {
      if (error.code && i18n.exists(`auth.err.${error.code}`)) return t(`auth.err.${error.code}`);
      if (error.status === 429) return t("auth.err.too_many");
      return error.message;
    }
    return t("common.error");
  };
}
