import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { useReminders } from "../api/care";
import { useTestHistory } from "../api/hooks";
import type { Result, TestInfo } from "../api/types";
import { ReminderForm, useDueText } from "../components/care/Reminders";
import { useSpan } from "../components/insights/ResultRow";
import { StatusMark } from "../components/insights/StatusMark";
import { TrendChart } from "../components/insights/TrendChart";
import { Button, Card, EmptyState, ErrorNote, Loading } from "../components/ui";
import { ageBand, formatDate, formatMonth, formatPercent, formatRange, formatUnit, formatValue, ordinal } from "../lib/format";
import NotFound from "./NotFound";

export default function TestHistory() {
  const { id = "", code = "" } = useParams();
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const history = useTestHistory(id, code);

  if (history.isPending) return <Loading />;
  if (history.isError) {
    if (history.error instanceof ApiError && history.error.status === 404) return <NotFound />;
    return <ErrorNote error={history.error} onRetry={() => void history.refetch()} />;
  }
  const { test, person, results } = history.data;
  const latest = results[results.length - 1];

  return (
    <div className="mx-auto max-w-4xl">
      <Link to={latest ? `/r/${latest.report_id}` : `/p/${id}`} className="text-link">
        ← {latest ? t("history.back_to_results") : person.display_name}
      </Link>
      <h1 className="mt-2 font-display text-3xl font-bold sm:text-4xl">{test.name}</h1>
      <p className="mt-1 text-muted">{person.display_name}</p>

      {!latest ? (
        <EmptyState title={test.name} body={t("history.few_results", { count: 0 })} />
      ) : (
        <>
          <div className="mt-6 flex flex-wrap items-end gap-x-8 gap-y-2">
            <div>
              <p className="text-sm text-muted">{t("history.latest")} · {formatDate(latest.date, lang)}</p>
              <p className="text-4xl font-semibold">
                {formatValue(latest.value, test.decimals)} <span className="text-lg font-normal text-muted">{formatUnit(test.unit)}</span>
              </p>
            </div>
            <StatusMark status={latest.status} className="text-base" />
            {latest.change?.fraction != null && latest.previous && (
              <p className="text-muted">
                {t("insights.change_since", { change: formatPercent(latest.change.fraction), date: formatDate(latest.previous.date, lang) })}
              </p>
            )}
          </div>

          <Card className="mt-6 p-4">
            <TrendChart results={results} test={test} />
          </Card>

          <Card className="mt-6 space-y-3 p-6">
            <TrendStatement latest={latest} test={test} count={results.length} />
            {test.rcv_up != null && test.rcv_down != null && (
              <p className="text-muted">
                {t("history.rcv", { up: formatPercent(test.rcv_up), down: formatPercent(test.rcv_down).replace("−", "") })}
              </p>
            )}
            <PercentileStatement latest={latest} />
          </Card>

          <RepeatReminder profileId={id} test={test} />

          <section className="mt-8" aria-labelledby="table-h">
            <h2 id="table-h" className="mb-3 font-display text-xl font-bold">{t("history.table_title")}</h2>
            <div className="overflow-x-auto rounded-lg border border-hairline bg-raised">
              <table className="w-full text-left">
                <thead className="border-b border-hairline text-sm text-muted">
                  <tr>
                    <th className="px-4 py-2 font-medium">{t("history.date")}</th>
                    <th className="px-4 py-2 font-medium">{t("history.value")}</th>
                    <th className="px-4 py-2 font-medium">{t("history.range")}</th>
                    <th className="px-4 py-2 font-medium">{t("history.status")}</th>
                    <th className="px-4 py-2 font-medium">{t("history.report")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-hairline">
                  {[...results].reverse().map((r) => (
                    <tr key={r.observation_id}>
                      <td className="px-4 py-2 whitespace-nowrap">{formatDate(r.date, lang)}</td>
                      <td className="tabular px-4 py-2 whitespace-nowrap">{formatValue(r.value, r.decimals)} {formatUnit(r.unit)}</td>
                      <td className="tabular px-4 py-2 whitespace-nowrap text-muted">{formatRange(r.ref_low, r.ref_high)}</td>
                      <td className="px-4 py-2"><StatusMark status={r.status} /></td>
                      <td className="px-4 py-2"><Link to={`/r/${r.report_id}`} className="text-link">{t("history.open")}</Link></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  );
}

/** "Remind me to repeat this test": the family's own date, usually the one the doctor gave. */
function RepeatReminder({ profileId, test }: { profileId: string; test: TestInfo }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const [adding, setAdding] = useState(false);
  const due = useDueText();
  const next = useReminders(profileId).data?.find((r) => r.test_code === test.code && !r.done_at);
  if (adding) {
    return (
      <div className="mt-6">
        <ReminderForm profileId={profileId} onDone={() => setAdding(false)}
          preset={{ title: t("reminders.repeat_test", { test: test.name }), test_code: test.code }} />
      </div>
    );
  }
  return (
    <div className="mt-6 flex flex-wrap items-center gap-x-4 gap-y-2">
      {next && (
        <p>
          {t("reminders.set_for", { title: next.title, date: formatDate(next.due_on, lang) })}{" "}
          <span className="text-muted">({due(next.due_on)})</span>
        </p>
      )}
      <Button onClick={() => setAdding(true)}>{t(next ? "reminders.another" : "reminders.remind_me")}</Button>
    </div>
  );
}

function TrendStatement({ latest, test, count }: { latest: Result; test: TestInfo; count: number }) {
  const { t, i18n } = useTranslation();
  const span = useSpan();
  const tr = latest.trend;
  if (!tr) return <p>{t("history.few_results", { count })}</p>;
  if (!tr.confirmed) return <p>{t(`history.reason_${tr.reason || "not_significant"}`)}</p>;
  const slope = `${formatValue(Math.abs(tr.slope_per_year), Math.max(test.decimals, 1))} ${formatUnit(test.unit)}`;
  return (
    <>
      <p className="font-medium">
        {t(tr.direction === "rising" ? "history.trend_rising" : "history.trend_falling", { slope, span: span(tr.first, tr.last) })}
      </p>
      {tr.projection && (
        <p>
          {t(`history.projection_${tr.projection.kind}_${tr.projection.limit}`, {
            value: formatValue(tr.projection.value, test.decimals), date: formatMonth(tr.projection.on, i18n.resolvedLanguage ?? "en"),
          })}{" "}
          <span className="text-muted">{t("history.projection_note")}</span>
        </p>
      )}
    </>
  );
}

function PercentileStatement({ latest }: { latest: Result }) {
  const { t } = useTranslation();
  const p = latest.percentile;
  if (!p) return null;
  const group = `${t(`history.group_${p.sex}`, { band: ageBand(p.age_band) })}`;
  const key = p.side === "below" ? "history.percentile_below" : p.side === "above" ? "history.percentile_above" : "history.percentile";
  return (
    <p>
      {t(key, { p: ordinal(p.value), group: `US ${group}` })}{" "}
      <span className="text-muted">{t("history.percentile_note", { population: p.population })}</span>
    </p>
  );
}
