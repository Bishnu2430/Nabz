import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { useLogout, useMe, useResendVerification, useUpdateLanguage, type Me } from "../api/auth";
import type { Lang } from "../api/types";
import { LANGUAGES } from "../i18n";
import { useTheme } from "../lib/theme";

export function AppShell() {
  const { t, i18n } = useTranslation();
  const [theme, toggleTheme] = useTheme();
  const next = theme === "light" ? t("nav.theme_dark") : t("nav.theme_light");
  const me = useMe().data;
  const saveLanguage = useUpdateLanguage();
  const changeLanguage = (lang: string) => {
    void i18n.changeLanguage(lang);
    if (me && me.preferred_language !== lang) saveLanguage.mutate(lang as Lang);
  };

  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-raised focus:px-3 focus:py-2">
        {t("common.skip")}
      </a>

      {import.meta.env.DEV && (
        <p className="bg-sunken px-4 py-1.5 text-center text-sm text-muted">{t("app.dev_banner")}</p>
      )}

      <header className="border-b border-hairline">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <Link to={me ? "/home" : "/"} className="flex items-center gap-2.5 no-underline">
            <img src="/seal.svg" alt="" className="size-8" />
            <span className="font-display text-2xl font-bold tracking-wide">Nabz</span>
          </Link>
          {me && !me.totp_required && <nav aria-label="Main">
            <NavLink
              to="/home"
              className={({ isActive }) =>
                `rounded px-2 py-1 ${isActive ? "text-ink underline decoration-accent decoration-2 underline-offset-8" : "text-muted hover:text-ink"}`
              }
            >
              {t("nav.family")}
            </NavLink>
          </nav>}
          <div className="ml-auto flex items-center gap-2">
            <label className="sr-only" htmlFor="lang">{t("nav.language")}</label>
            <select
              id="lang"
              value={i18n.resolvedLanguage}
              onChange={(e) => changeLanguage(e.target.value)}
              className="rounded-md border border-hairline bg-raised px-2 py-1.5 text-sm"
            >
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>{l.label}</option>
              ))}
            </select>
            <button
              type="button"
              onClick={toggleTheme}
              aria-label={t("nav.switch_theme", { theme: next })}
              title={next}
              className="grid size-9 place-items-center rounded-md border border-hairline bg-raised hover:border-ink/40"
            >
              {theme === "light" ? <MoonIcon /> : <SunIcon />}
            </button>
            {me ? <AccountMenu me={me} /> : <SignInLink />}
          </div>
        </div>
      </header>

      {me && !me.email_verified && <VerifyBanner me={me} />}

      <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        <Outlet />
      </main>

      <footer className="border-t border-hairline">
        <div className="mx-auto flex max-w-6xl flex-wrap items-baseline gap-x-6 gap-y-2 px-4 py-4 text-sm text-muted">
          <p className="mr-auto">{t("app.disclaimer")}</p>
          <span className="flex gap-x-6">
            <Link to="/privacy" className="text-muted hover:text-ink">{t("legal.privacy_title")}</Link>
            <Link to="/safety" className="text-muted hover:text-ink">{t("legal.safety_title")}</Link>
          </span>
        </div>
      </footer>
    </div>
  );
}

function SignInLink() {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  if (pathname === "/login") return null;
  return (
    <Link to="/login" className="rounded-md border border-hairline bg-raised px-3 py-1.5 font-medium no-underline hover:border-ink/40">
      {t("auth.sign_in")}
    </Link>
  );
}

/** The account's menu: who is signed in, settings, sign out. Closes on Escape and on a click outside. */
function AccountMenu({ me }: { me: Me }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const logout = useLogout();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent ? e.key === "Escape" : !ref.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [open]);

  const initial = me.email.charAt(0).toUpperCase();
  return (
    <div ref={ref} className="relative">
      <button type="button" aria-expanded={open} aria-haspopup="true" onClick={() => setOpen(!open)}
        aria-label={t("nav.account_menu", { email: me.email })}
        className="grid size-9 place-items-center rounded-full border border-hairline bg-raised font-display font-bold hover:border-ink/40">
        {initial}
      </button>
      {open && (
        <div className="absolute right-0 z-20 mt-2 w-64 rounded-lg border border-hairline bg-raised p-2 shadow-lg">
          <p className="truncate px-3 py-2 text-sm text-muted">{me.email}</p>
          <Link to="/settings" onClick={() => setOpen(false)}
            className="block rounded-md px-3 py-2 no-underline hover:bg-sunken">{t("nav.settings")}</Link>
          <button type="button" disabled={logout.isPending}
            onClick={() => logout.mutate(undefined, { onSettled: () => navigate("/", { replace: true }) })}
            className="block w-full rounded-md px-3 py-2 text-left hover:bg-sunken">
            {t("nav.sign_out")}
          </button>
        </div>
      )}
    </div>
  );
}

/** Until the email is confirmed, uploads are refused (docs/12 §3); say so before anyone tries. */
function VerifyBanner({ me }: { me: Me }) {
  const { t } = useTranslation();
  const resend = useResendVerification();
  return (
    <div className="border-b border-borderline/40 bg-borderline/10">
      <p className="mx-auto max-w-6xl px-4 py-2 text-sm">
        {t("auth.verify_banner", { email: me.email })}{" "}
        {resend.isSuccess ? (
          <span className="text-normal">{t("settings.resent")}</span>
        ) : (
          <button type="button" className="text-link underline" disabled={resend.isPending} onClick={() => resend.mutate()}>
            {t("settings.resend")}
          </button>
        )}
      </p>
    </div>
  );
}

function MoonIcon() {
  return (
    <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z" strokeLinejoin="round" />
    </svg>
  );
}

function SunIcon() {
  return (
    <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4" />
    </svg>
  );
}
