import { useTranslation } from "react-i18next";

import type { SharedReport } from "../../api/types";
import { useExact } from "../exact/exact";
import { organIcon, Icon } from "../icons";
import { RangeBar } from "../insights/RangeBar";
import { StatusMark, isAbnormal } from "../insights/StatusMark";
import { Card } from "../ui";
import { formatDate, formatPercent, formatRange, formatWithUnit } from "../../lib/format";

/**
 * One report as a doctor reads it, read-only: the person, critical results first, every organ system with exact
 * values, the lab's range and the change since last time, the family's note and the questions they prepared. Shown
 * through a share link and to a clinician the report was shared with.
 */
export function SharedReportView({ d }: { d: SharedReport }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const { describe } = useExact();
  const name = (o: { names: Record<string, string> }) => o.names[lang] ?? o.names.en;
  return (
    <>
      <header className="border-b-2 border-ink pb-3">
        <h1 className="font-display text-3xl font-bold">{d.person.display_name}</h1>
        <p className="mt-1 text-muted">
          {[d.person.age != null && t("summary.age", { count: d.person.age }), t(`profile_form.sex_${d.person.sex}`),
            d.lab_name, d.collected_at && formatDate(d.collected_at, lang)].filter(Boolean).join(" · ")}
        </p>
        {d.note && <p className="mt-2"><span className="text-muted">{t("shared.note")}:</span> “{d.note}”</p>}
      </header>

      {d.critical.length > 0 && (
        <section role="alert" className="mt-5 rounded-lg border-2 border-critical bg-critical/5 p-4">
          <h2 className="font-display text-xl font-bold text-critical">{t("critical.list")}</h2>
          <ul className="mt-1 space-y-0.5">
            {d.critical.map((r) => (
              <li key={r.observation_id}><span className="font-medium">{r.test_name}</span>{" "}
                <span className="tabular">{formatWithUnit(r)}</span>, {describe(r)}</li>
            ))}
          </ul>
        </section>
      )}

      <div className="stagger mt-6 space-y-6">
        {d.organs.map((o) => (
          <section key={o.code} aria-labelledby={`sh-${o.code}`}>
            <div className="mb-2 flex items-baseline justify-between gap-3">
              <h2 id={`sh-${o.code}`} className="flex items-center gap-2 font-display text-xl font-bold">
                <Icon name={organIcon(o.code)} size={20} className="text-muted" />{name(o)}
              </h2>
              <StatusMark status={o.status} />
            </div>
            <Card className="divide-y divide-hairline">
              {o.results.map((r) => (
                <div key={r.observation_id} className="grid items-center gap-x-4 gap-y-1 px-4 py-2.5 sm:grid-cols-[minmax(0,2fr)_auto_auto_minmax(0,2fr)]">
                  <span className="font-medium">{r.test_name}</span>
                  <span className={`tabular text-lg ${isAbnormal(r.status) ? "font-semibold text-abnormal" : ""}`}>
                    {formatWithUnit(r)}
                  </span>
                  <RangeBar value={Number(r.value)} low={r.ref_low == null ? null : Number(r.ref_low)}
                    high={r.ref_high == null ? null : Number(r.ref_high)} status={r.status} />
                  <span className="text-sm text-muted">
                    {isAbnormal(r.status) ? describe(r) : formatRange(r.ref_low, r.ref_high)}
                    {r.previous && r.change?.fraction != null && (
                      <> · {t("insights.change_since", { change: formatPercent(r.change.fraction), date: formatDate(r.previous.date, lang) })}</>
                    )}
                  </span>
                </div>
              ))}
            </Card>
          </section>
        ))}
      </div>

      {d.questions.length > 0 && (
        <section className="mt-8" aria-labelledby="sh-q">
          <h2 id="sh-q" className="mb-2 font-display text-xl font-bold">{t("shared.questions")}</h2>
          <ol className="list-decimal space-y-1 pl-5">{d.questions.map((q) => <li key={q}>{q}</li>)}</ol>
        </section>
      )}

      <p className="mt-8 border-t border-hairline pt-3 text-sm text-muted">{t("shared.footer")}</p>
    </>
  );
}
