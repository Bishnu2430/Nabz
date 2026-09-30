import { useTranslation } from "react-i18next";

const MAILPIT = import.meta.env.VITE_MAILPIT_URL ?? "http://localhost:8025";

/** In development every email lands in Mailpit (docs/12 §3), so say where to look. */
export function MailHint() {
  const { t } = useTranslation();
  if (!import.meta.env.DEV) return null;
  return (
    <p className="rounded-md bg-sunken px-4 py-3 text-sm text-muted">
      {t("auth.mailpit")}{" "}
      <a href={MAILPIT} target="_blank" rel="noreferrer" className="text-link">{MAILPIT}</a>
    </p>
  );
}
