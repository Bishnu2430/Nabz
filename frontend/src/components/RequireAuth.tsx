import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, Outlet, useLocation, useSearchParams } from "react-router-dom";

import { safeNext, useMe, type Role } from "../api/auth";
import { EmptyState, ErrorNote, Loading } from "./ui";

/** Signed-in pages. Staff without two-step sign-in can reach only its set-up in settings (docs/12 §3). */
export function RequireAuth() {
  const me = useMe();
  const location = useLocation();

  if (me.isPending) return <Loading />;
  if (me.isError) return <ErrorNote error={me.error} onRetry={() => void me.refetch()} />;
  if (!me.data) {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?next=${next}`} replace />;
  }
  if (me.data.totp_required && location.pathname !== "/settings") return <Navigate to="/settings#security" replace />;
  return <Outlet />;
}

/** Staff areas (FR-39): anyone else is told plainly, without learning more than that. */
export function RequireRole({ roles }: { roles: Role[] }) {
  const { t } = useTranslation();
  const me = useMe().data;
  if (!me || !roles.includes(me.role)) {
    return <EmptyState title={t("console.forbidden_title")} body={t("console.forbidden_body")} />;
  }
  return <Outlet />;
}

/** Sign-in and sign-up make no sense when signed in: go where the person was heading, or to their family. */
export function RedirectIfSignedIn({ children }: { children: ReactNode }) {
  const me = useMe();
  const [params] = useSearchParams();
  if (me.isPending) return <Loading />;
  if (me.data) return <Navigate to={safeNext(params.get("next"))} replace />;
  return <>{children}</>;
}
