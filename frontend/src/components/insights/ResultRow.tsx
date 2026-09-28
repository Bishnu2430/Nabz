import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import type { Result } from "../../api/types";
import {
  ageBand, formatDate, formatPercent, formatRange, formatUnit, formatValue, ordinal, spanYears,
} from "../../lib/format";
import { RangeBar } from "./RangeBar";
import { StatusMark } from "./StatusMark";

export function useSpan() {
  const { t } = useTranslation();
  return (first: string, last: string) => {
    const years = spanYears(first, last);
    return years >= 1.5
      ? t("insights.years", { count: Math.round(years) })
      : t("insights.months", { count: Math.max(1, Math.round(years * 12)) });
  };
}

/** One result: value, status, where it sits in its range, the change since last time, trend and percentile. */
export function ResultRow({ result, profileId }: { result: Result; profileId: string }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const span = useSpan();
  const r = result;
  const range = formatRange(r.ref_low, r.ref_high);
  const unit = formatUnit(r.unit);

  return (
    <li className="py-3">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <Link to={`/p/${profileId}/tests/${r.test_code}`} className="font-medium text-ink hover:text-link hover:underline">
          {r.test_name}
        </Link>
        <StatusMark status={r.status} />
      </div>
      <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1">
        <p className="tabular text-xl font-medium">
          {formatValue(r.value, r.decimals)} <span className="text-sm font-normal text-muted">{unit}</span>
        </p>
        <RangeBar value={Number(r.value)} low={r.ref_low == null ? null : Number(r.ref_low)}
          high={r.ref_high == null ? null : Number(r.ref_high)} status={r.status} />
        {range && (
          <p className="text-sm text-muted">
            <span className="tabular">{range}</span>{" "}
            ({r.ref_source === "report" ? t("insights.range_report") : t("insights.range_typical")})
          </p>
        )}
      </div>
      <ul className="mt-1 space-y-0.5 text-sm text-muted">
        {r.change && r.previous ? (
          <li>
            {t("insights.change_since", { change: formatPercent(r.change.fraction ?? 0), date: formatDate(r.previous.date, lang) })}
            {r.change.significant != null && (
              <> · <span className={r.change.significant ? "font-medium text-ink" : ""}>
                {r.change.significant ? t("insights.significant") : t("insights.not_significant")}
              </span></>
            )}
          </li>
        ) : (
          <li>{t("insights.first_result")}</li>
        )}
        {r.trend?.confirmed && (
          <li className="font-medium text-ink">
            {t(r.trend.direction === "rising" ? "insights.trend_rising" : "insights.trend_falling",
              { span: span(r.trend.first, r.trend.last) })}
          </li>
        )}
        {r.percentile && (
          <li>
            {t("insights.percentile", {
              p: r.percentile.side === "below" ? "< 5th" : r.percentile.side === "above" ? "> 95th" : ordinal(r.percentile.value),
              group: t(`history.group_${r.percentile.sex}`, { band: ageBand(r.percentile.age_band) }),
            })}
          </li>
        )}
        {r.flag_disagrees && <li>{t("insights.flag_disagrees")}</li>}
      </ul>
    </li>
  );
}
