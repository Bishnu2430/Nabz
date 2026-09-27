import { useTranslation } from "react-i18next";
import { Link, NavLink, Outlet } from "react-router-dom";

import { LANGUAGES } from "../i18n";
import { useTheme } from "../lib/theme";

export function AppShell() {
  const { t, i18n } = useTranslation();
  const [theme, toggleTheme] = useTheme();
  const next = theme === "light" ? t("nav.theme_dark") : t("nav.theme_light");

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
          <Link to="/home" className="flex items-center gap-2.5 no-underline">
            <img src="/seal.svg" alt="" className="size-8" />
            <span className="font-display text-2xl font-bold tracking-wide">Nabz</span>
          </Link>
          <nav aria-label="Main">
            <NavLink
              to="/home"
              className={({ isActive }) =>
                `rounded px-2 py-1 ${isActive ? "text-ink underline decoration-accent decoration-2 underline-offset-8" : "text-muted hover:text-ink"}`
              }
            >
              {t("nav.family")}
            </NavLink>
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <label className="sr-only" htmlFor="lang">{t("nav.language")}</label>
            <select
              id="lang"
              value={i18n.resolvedLanguage}
              onChange={(e) => void i18n.changeLanguage(e.target.value)}
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
          </div>
        </div>
      </header>

      <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        <Outlet />
      </main>

      <footer className="border-t border-hairline">
        <p className="mx-auto max-w-6xl px-4 py-4 text-sm text-muted">{t("app.disclaimer")}</p>
      </footer>
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
