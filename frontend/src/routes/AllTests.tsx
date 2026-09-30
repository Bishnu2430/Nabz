import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { useBodyMap, useProfiles } from "../api/hooks";
import { ORGAN_ORDER } from "../components/body/organs";
import { useExact } from "../components/exact/exact";
import { Sparkline } from "../components/exact/Sparkline";
import { StatusMark, isAbnormal } from "../components/insights/StatusMark";
import { Card, ErrorNote, fieldClass, Loading, PageTitle } from "../components/ui";
import { formatDate, formatWithUnit } from "../lib/format";
import { seriesByTest } from "../lib/series";

/** Every test a person has had: latest value, how it sits in its range, a small chart, and a search box. */
export default function AllTests() {
  const { id = "" } = useParams();
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const profile = useProfiles().data?.find((p) => p.id === id);
  const frames = useBodyMap(id);
  const { describe } = useExact();
  const [query, setQuery] = useState("");
  const [onlyOut, setOnlyOut] = useState(false);
  const series = useMemo(() => seriesByTest(frames.data ?? []), [frames.data]);

  if (frames.isPending) return <Loading />;
  if (frames.isError) return <ErrorNote error={frames.error} />;

  const q = query.trim().toLowerCase();
  const shown = series.filter((s) => (!onlyOut || isAbnormal(s.latest.status))
    && (!q || `${s.latest.test_name} ${s.latest.short_name} ${t(`organs.${s.organ}`)}`.toLowerCase().includes(q)));
  const byOrgan = ORGAN_ORDER.map((code) => [code, shown.filter((s) => s.organ === code)] as const)
    .filter(([, items]) => items.length > 0);

  return (
    <>
      <Link to={`/p/${id}`} className="text-link">← {profile?.display_name}</Link>
      <PageTitle title={t("tests_page.title")} subtitle={t("tests_page.subtitle", { count: series.length })} />
      <div className="mb-6 flex flex-wrap items-center gap-4">
        <label className="min-w-64 flex-1">
          <span className="sr-only">{t("tests_page.search")}</span>
          <input type="search" value={query} onChange={(e) => setQuery(e.target.value)} className={fieldClass}
            placeholder={t("tests_page.search")} />
        </label>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={onlyOut} onChange={(e) => setOnlyOut(e.target.checked)}
            className="size-4 accent-[var(--accent)]" />
          {t("tests_page.only_out")}
        </label>
      </div>
      {byOrgan.length === 0 && <p className="text-muted">{t("tests_page.none")}</p>}
      <div className="space-y-8">
        {byOrgan.map(([organ, items]) => (
          <section key={organ} aria-labelledby={`org-${organ}`}>
            <h2 id={`org-${organ}`} className="mb-3 font-display text-xl font-bold">{t(`organs.${organ}`)}</h2>
            <Card className="divide-y divide-hairline">
              {items.map((s) => (
                <Link key={s.code} to={`/p/${id}/tests/${s.code}`}
                  className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-1 px-4 py-3 text-ink no-underline hover:bg-sunken/50 sm:grid-cols-[minmax(0,2fr)_auto_minmax(0,2fr)_auto]">
                  <span>
                    <span className="block font-medium">{s.latest.test_name}</span>
                    <span className="block text-sm text-muted">
                      {t("tests_page.results", { count: s.results.length, date: formatDate(s.latest.date, lang) })}
                    </span>
                  </span>
                  <span className="tabular text-right text-lg font-medium">{formatWithUnit(s.latest)}</span>
                  <span className="text-sm">
                    <StatusMark status={s.latest.status} /> <span className="text-muted">{describe(s.latest)}</span>
                  </span>
                  <Sparkline width={110} height={30}
                    points={s.results.map((r) => ({ date: r.date, value: Number(r.value), status: r.status }))}
                    low={s.latest.ref_low == null ? null : Number(s.latest.ref_low)}
                    high={s.latest.ref_high == null ? null : Number(s.latest.ref_high)} />
                </Link>
              ))}
            </Card>
          </section>
        ))}
      </div>
    </>
  );
}
