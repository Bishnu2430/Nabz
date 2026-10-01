import clsx from "clsx";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { useOrganHistory } from "../../api/hooks";
import type { Result } from "../../api/types";
import { deviation, formatDate, formatPercent, formatRange, formatWithUnit } from "../../lib/format";
import { useExact } from "../exact/exact";
import { Sparkline } from "../exact/Sparkline";
import { useSpan } from "../insights/ResultRow";
import { STATUS_COLOR, StatusMark, isAbnormal } from "../insights/StatusMark";
import { Card, ErrorNote, Loading } from "../ui";
import type { OrganCode } from "./organs";

const SEVERITY: Record<string, number> = { critical_low: 3, critical_high: 3, low: 2, high: 2, normal: 1, unknown: 0 };

interface Line {
  latest: Result;
  series: Result[];
}

/**
 * One organ system on one report (FR-28): each of its tests as a small chart with the exact value, how far it is
 * from the range, the change since the previous result and the trend. Results beyond a critical limit first, then
 * the rest outside the range, then those in range.
 */
export function OrganPanel({ profileId, organ, name, reportId, onBack, extra }: {
  profileId: string;
  organ: OrganCode;
  name: string;
  /** The report the body map is showing: each test's latest result is the one from this report. */
  reportId: string;
  onBack: () => void;
  extra?: ReactNode;
}) {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const history = useOrganHistory(profileId, organ);

  let body: ReactNode;
  if (history.isPending) body = <Loading />;
  else if (history.isError) body = <ErrorNote error={history.error} />;
  else {
    const lines: Line[] = [];
    for (const h of history.data.tests) {
      const at = h.results.findIndex((r) => r.report_id === reportId);
      if (at >= 0) lines.push({ latest: h.results[at], series: h.results.slice(0, at + 1) });
    }
    const gap = (r: Result) => deviation(r)?.fraction ?? 0;
    lines.sort((a, b) => SEVERITY[b.latest.status] - SEVERITY[a.latest.status] || gap(b.latest) - gap(a.latest));
    const outside = lines.filter((l) => isAbnormal(l.latest.status));
    const inside = lines.filter((l) => !isAbnormal(l.latest.status));
    const date = lines[0]?.latest.date;
    body = (
      <>
        <p className="text-sm text-muted">
          {date && t("organ.as_of", { date: formatDate(date, lang) })} ·{" "}
          {t("organ.summary", { count: lines.length, out: outside.length })}
        </p>
        {outside.length > 0 && (
          <section className="mt-4" aria-labelledby="organ-out-h">
            <h4 id="organ-out-h" className="mb-2 text-sm font-semibold uppercase tracking-wide text-abnormal">
              {t("organ.outside")}
            </h4>
            <ul className="space-y-3">
              {outside.map((l) => <li key={l.latest.test_code}><ChartCard line={l} profileId={profileId} /></li>)}
            </ul>
          </section>
        )}
        {inside.length > 0 && (
          <section className="mt-5" aria-labelledby="organ-in-h">
            <h4 id="organ-in-h" className="mb-1 text-sm font-semibold uppercase tracking-wide text-normal">
              {t("organ.inside")}
            </h4>
            <ul className="divide-y divide-hairline">
              {inside.map((l) => <li key={l.latest.test_code}><CompactRow line={l} profileId={profileId} /></li>)}
            </ul>
          </section>
        )}
        {extra && <div className="mt-5">{extra}</div>}
      </>
    );
  }

  return (
    <Card className="slide-in overflow-hidden">
      <div className="flex">
        <div aria-hidden="true" className="w-1.5 shrink-0"
          style={{ background: history.data ? STATUS_COLOR[worstOf(history.data.tests, reportId)] : "var(--hairline)" }} />
        <div className="min-w-0 flex-1 p-5">
          <button type="button" onClick={onBack} className="mb-2 text-sm text-link hover:underline">
            ← {t("organ.back")}
          </button>
          <h3 className="font-display text-2xl font-bold">{name}</h3>
          <div className="mt-1">{body}</div>
        </div>
      </div>
    </Card>
  );
}

function worstOf(tests: { results: Result[] }[], reportId: string) {
  let worst: Result["status"] = "unknown";
  for (const h of tests) {
    const r = h.results.find((x) => x.report_id === reportId);
    if (r && SEVERITY[r.status] > SEVERITY[worst]) worst = r.status;
  }
  return worst;
}

function ChartCard({ line, profileId }: { line: Line; profileId: string }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const { describe } = useExact();
  const span = useSpan();
  const r = line.latest;
  const critical = r.status.startsWith("critical");
  return (
    <div className={clsx("rounded-md border p-3", critical ? "border-critical/60 bg-critical/5" : "border-abnormal/30")}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="font-medium">{r.test_name}</span>
        <StatusMark status={r.status} />
      </div>
      <div className="mt-1 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="tabular text-2xl font-semibold">{formatWithUnit(r)}</p>
          <p className={clsx("text-sm", critical ? "font-medium text-critical" : "text-abnormal")}>{describe(r)}</p>
          <p className="text-sm text-muted">
            {t("organ.range", { range: formatRange(r.ref_low, r.ref_high) || "—" })}
          </p>
        </div>
        <Sparkline points={line.series.map((s) => ({ date: s.date, value: Number(s.value), status: s.status }))}
          low={r.ref_low == null ? null : Number(r.ref_low)} high={r.ref_high == null ? null : Number(r.ref_high)} />
      </div>
      <ul className="mt-2 space-y-0.5 text-sm text-muted">
        {r.previous && r.change?.fraction != null && (
          <li>
            {t("organ.since", {
              change: formatPercent(r.change.fraction), date: formatDate(r.previous.date, lang),
              previous: formatWithUnit({ value: String(r.previous.value), decimals: r.decimals, unit: r.unit }),
            })}
            {r.change.significant && <> · <span className="font-medium text-ink">{t("insights.significant")}</span></>}
          </li>
        )}
        {r.trend?.confirmed && (
          <li className="font-medium text-ink">
            {t(r.trend.direction === "rising" ? "insights.trend_rising" : "insights.trend_falling",
              { span: span(r.trend.first, r.trend.last) })}
          </li>
        )}
        {line.series.length > 1 && (
          <li>{t("organ.results_since", { count: line.series.length, date: formatDate(line.series[0].date, lang) })}</li>
        )}
      </ul>
      <Link to={`/p/${profileId}/tests/${r.test_code}`} className="mt-1 inline-block text-sm text-link">
        {t("organ.full_history")} →
      </Link>
    </div>
  );
}

function CompactRow({ line, profileId }: { line: Line; profileId: string }) {
  const r = line.latest;
  return (
    <Link to={`/p/${profileId}/tests/${r.test_code}`}
      className="flex items-center gap-3 py-2 text-ink no-underline hover:bg-sunken/60">
      <span className="min-w-0 flex-1">
        <span className="block truncate">{r.test_name}</span>
        <span className="tabular block text-sm text-muted">{formatRange(r.ref_low, r.ref_high)}</span>
      </span>
      <span className="tabular font-medium">{formatWithUnit(r)}</span>
      <Sparkline width={72} height={24}
        points={line.series.map((s) => ({ date: s.date, value: Number(s.value), status: s.status }))}
        low={r.ref_low == null ? null : Number(r.ref_low)} high={r.ref_high == null ? null : Number(r.ref_high)} />
    </Link>
  );
}
