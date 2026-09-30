import { useTranslation } from "react-i18next";

/**
 * The privacy notice and "what Nabz is and is not" (docs/10 §3, docs/12 §6). Short, plain and in the reader's
 * language; the sections are translation keys so each language keeps the same structure.
 */
const PAGES = {
  privacy: ["collect", "why", "where", "ai", "keep", "rights", "contact"],
  safety: ["is", "is_not", "checks", "critical", "doctor"],
} as const;

export default function Legal({ page }: { page: keyof typeof PAGES }) {
  const { t } = useTranslation();
  return (
    <article className="mx-auto max-w-2xl">
      <h1 className="font-display text-3xl font-bold sm:text-4xl">{t(`legal.${page}_title`)}</h1>
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
