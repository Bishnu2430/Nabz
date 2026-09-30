import { useMemo, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { useBodyMap, useExplanation, useProfiles, useRecords, useReports, useWatch } from "../api/hooks";
import { ORGAN_ORDER } from "../components/body/organs";
import { useExact } from "../components/exact/exact";
import { StatusIcon, isAbnormal } from "../components/insights/StatusMark";
import { Button, ErrorNote, Loading } from "../components/ui";
import { formatDate, formatPercent, formatRange, formatWithUnit } from "../lib/format";
import { seriesByTest } from "../lib/series";

/**
 * A one-page summary to take to a doctor, printable or saved as PDF from the browser (FR-32): what is outside its
 * range now, what has changed, every latest value, other records, the family's notes and questions to ask.
 */
export default function Summary() {
  const { id = "" } = useParams();
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const profile = useProfiles().data?.find((p) => p.id === id);
  const frames = useBodyMap(id);
  const reports = useReports(id).data ?? [];
  const watch = useWatch(id).data ?? [];
  const records = useRecords(id).data ?? [];
  const latestReport = frames.data?.at(-1)?.report_id ?? "";
  const questions = useExplanation(latestReport, lang).data?.explanation?.doctor_questions ?? [];
  const { describe } = useExact();
  const series = useMemo(() => seriesByTest(frames.data ?? []), [frames.data]);

  if (frames.isPending || !profile) return <Loading />;
  if (frames.isError) return <ErrorNote error={frames.error} />;

  const now = series.filter((s) => isAbnormal(s.latest.status));
  const age = profile.date_of_birth
    ? Math.floor((Date.now() - Date.parse(profile.date_of_birth)) / (365.25 * 86400000)) : null;
  const notes = reports.filter((r) => r.note);

  return (
    <article className="mx-auto max-w-3xl print:max-w-none">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3 print:hidden">
        <Link to={`/p/${id}`} className="text-link">← {profile.display_name}</Link>
        <Button variant="primary" onClick={() => window.print()}>{t("summary.print")}</Button>
      </div>

      <header className="border-b-2 border-ink pb-3">
        <h1 className="font-display text-3xl font-bold">{t("summary.title", { name: profile.display_name })}</h1>
        <p className="mt-1 text-muted">
          {[age != null && t("summary.age", { count: age }), t(`profile_form.sex_${profile.sex}`),
            t("summary.reports", { count: frames.data.length }),
            frames.data.length > 0 && t("summary.span", { from: formatDate(frames.data[0].date, lang),
              to: formatDate(frames.data.at(-1)!.date, lang) })].filter(Boolean).join(" · ")}
        </p>
        <p className="text-sm text-muted">{t("summary.prepared", { date: formatDate(new Date().toISOString(), lang) })}</p>
      </header>

      <Section title={t("summary.now")}>
        {now.length === 0 ? <p>{t("summary.none_out")}</p> : (
          <ul className="space-y-1">
            {now.map((s) => (
              <li key={s.code} className="flex flex-wrap items-baseline gap-x-2">
                <span className="text-abnormal"><StatusIcon status={s.latest.status} /></span>
                <span className="font-medium">{s.latest.test_name}</span>
                <span className="tabular font-semibold">{formatWithUnit(s.latest)}</span>
                <span className="text-muted">{describe(s.latest)} · {formatDate(s.latest.date, lang)}</span>
              </li>
            ))}
          </ul>
        )}
      </Section>

      {watch.length > 0 && (
        <Section title={t("summary.changes")}>
          <ul className="space-y-1">
            {watch.map((w) => (
              <li key={w.test_code}>
                <span className="font-medium">{w.test_name}</span>{" "}
                <span className="tabular">{formatWithUnit(w.latest)}</span>
                {w.latest.change?.fraction != null && w.latest.previous && (
                  <span className="text-muted"> · {t("insights.change_since", {
                    change: formatPercent(w.latest.change.fraction), date: formatDate(w.latest.previous.date, lang) })}</span>
                )}
                {w.confirmed && w.direction && (
                  <span className="text-muted"> · {t(w.direction === "rising" ? "summary.rising" : "summary.falling")}</span>
                )}
              </li>
            ))}
          </ul>
        </Section>
      )}

      <Section title={t("summary.latest")}>
        <table className="w-full text-left text-sm">
          <thead className="text-muted">
            <tr className="border-b border-hairline">
              <th className="py-1 pr-3 font-medium">{t("compare.test")}</th>
              <th className="py-1 pr-3 font-medium">{t("history.value")}</th>
              <th className="py-1 pr-3 font-medium">{t("history.range")}</th>
              <th className="py-1 pr-3 font-medium">{t("history.date")}</th>
              <th className="py-1 font-medium">{t("summary.previous")}</th>
            </tr>
          </thead>
          {ORGAN_ORDER.map((organ) => {
            const rows = series.filter((s) => s.organ === organ);
            if (rows.length === 0) return null;
            return (
              <tbody key={organ} className="break-inside-avoid">
                <tr><th colSpan={5} className="pb-1 pt-3 font-display text-base">{t(`organs.${organ}`)}</th></tr>
                {rows.map((s) => {
                  const prev = s.results.at(-2);
                  const out = isAbnormal(s.latest.status);
                  return (
                    <tr key={s.code} className="border-b border-hairline/60">
                      <td className="py-1 pr-3">{s.latest.test_name}</td>
                      <td className={`tabular whitespace-nowrap py-1 pr-3 ${out ? "font-semibold text-abnormal" : ""}`}>
                        {out && <StatusIcon status={s.latest.status} />} {formatWithUnit(s.latest)}
                      </td>
                      <td className="tabular whitespace-nowrap py-1 pr-3 text-muted">{formatRange(s.latest.ref_low, s.latest.ref_high)}</td>
                      <td className="whitespace-nowrap py-1 pr-3 text-muted">{formatDate(s.latest.date, lang)}</td>
                      <td className="tabular py-1 text-muted">
                        {prev ? `${formatWithUnit(prev)} (${formatDate(prev.date, lang)})` : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            );
          })}
        </table>
      </Section>

      {records.length > 0 && (
        <Section title={t("records.title")}>
          <ul className="space-y-1">
            {records.map((r) => (
              <li key={r.id}>
                <span className="font-medium">{r.title}</span>
                <span className="text-muted"> · {[r.record_date && formatDate(r.record_date, lang), r.facility]
                  .filter(Boolean).join(" · ")}</span>
                {r.notes && <span className="text-muted"> · {r.notes}</span>}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {notes.length > 0 && (
        <Section title={t("summary.notes")}>
          <ul className="space-y-1">
            {notes.map((r) => (
              <li key={r.id}><span className="text-muted">{formatDate(r.collected_at ?? r.created_at, lang)}:</span> {r.note}</li>
            ))}
          </ul>
        </Section>
      )}

      {questions.length > 0 && (
        <Section title={t("explain.questions")}>
          <ol className="list-decimal space-y-1 pl-5">{questions.map((q) => <li key={q}>{q}</li>)}</ol>
        </Section>
      )}

      <p className="mt-8 border-t border-hairline pt-3 text-sm text-muted">{t("app.disclaimer")}</p>
    </article>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mt-6 break-inside-avoid-page">
      <h2 className="mb-2 font-display text-xl font-bold">{title}</h2>
      {children}
    </section>
  );
}
