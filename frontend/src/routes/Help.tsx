import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { Icon, IconSeal } from "../components/icons";

const GROUPS = [
  { id: "start", items: ["add", "check", "children"] },
  { id: "results", items: ["colours", "range", "critical", "change"] },
  { id: "explain", items: ["explanation", "ask", "listen", "languages"] },
  { id: "care", items: ["readings", "reminders", "card"] },
  { id: "share", items: ["share", "doctor", "offline"] },
  { id: "data", items: ["private", "delete"] },
] as const;

const LINKS: Partial<Record<string, { to: string; key: string }>> = {
  critical: { to: "/safety", key: "legal.safety_title" },
  private: { to: "/privacy", key: "legal.privacy_title" },
  delete: { to: "/settings", key: "nav.settings" },
};

/** Questions people ask, answered in a sentence or three, grouped the way the app is used. */
export default function Help() {
  const { t } = useTranslation();
  return (
    <article className="mx-auto max-w-2xl">
      <div className="page-head flex items-center gap-4">
        <IconSeal name="chat" size={24} className="icon-seal-lg" />
        <h1 className="font-display text-3xl font-bold sm:text-4xl">{t("help.title")}</h1>
      </div>
      <p className="mt-3 text-lg text-muted">{t("help.intro")}</p>
      {GROUPS.map((g) => (
        <section key={g.id} className="mt-8" aria-labelledby={`help-${g.id}`}>
          <h2 id={`help-${g.id}`} className="font-display text-xl font-bold">{t(`help.g_${g.id}`)}</h2>
          <div className="mt-2 divide-y divide-hairline rounded-lg border border-hairline bg-raised">
            {g.items.map((q) => (
              <details key={q} className="group px-4 py-3">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-3 font-medium">
                  {t(`help.q_${q}`)}
                  <Icon name="plus" size={16} className="shrink-0 text-muted transition-transform group-open:rotate-45" />
                </summary>
                <p className="mt-2 whitespace-pre-line text-muted">{t(`help.a_${q}`)}</p>
                {LINKS[q] && <Link to={LINKS[q]!.to} className="mt-1 inline-block text-sm text-link">{t(LINKS[q]!.key)} →</Link>}
              </details>
            ))}
          </div>
        </section>
      ))}
      <p className="mt-10 text-sm text-muted">
        {t("help.more")} <Link to="/about" className="text-link">{t("about.title")}</Link>
      </p>
    </article>
  );
}
