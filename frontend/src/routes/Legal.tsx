import { useTranslation } from "react-i18next";

import { IconSeal } from "../components/icons";

/**
 * The privacy notice, "what Nabz is and is not" and the terms of use (docs/10 §3, docs/12 §6). Short, plain and in the reader's
 * language; the sections are translation keys so each language keeps the same structure.
 */
const PAGES = {
  privacy: ["collect", "why", "where", "ai", "share", "keep", "rights", "contact"],
  safety: ["is", "is_not", "checks", "critical", "doctor"],
  terms: ["what", "account", "uploads", "explanations", "sharing", "doctors", "availability", "ending"],
} as const;
const ICONS = { privacy: "lock", safety: "shield", terms: "pen" } as const;

export default function Legal({ page }: { page: keyof typeof PAGES }) {
  const { t } = useTranslation();
  return (
    <article className="mx-auto max-w-2xl">
      <div className="page-head flex items-center gap-4">
        <IconSeal name={ICONS[page]} size={24} className="icon-seal-lg" />
        <h1 className="font-display text-3xl font-bold sm:text-4xl">{t(`legal.${page}_title`)}</h1>
      </div>
      <p className="mt-3 text-lg text-muted">{t(`legal.${page}_intro`)}</p>
      {PAGES[page].map((s) => (
        <section key={s} className="mt-8">
          <h2 className="font-display text-xl font-bold">{t(`legal.${page}_${s}_h`)}</h2>
          <p className="mt-2 whitespace-pre-line">{t(`legal.${page}_${s}`)}</p>
        </section>
      ))}
      <p className="mt-10 text-sm text-muted">{t("legal.version")}</p>
    </article>
  );
}
