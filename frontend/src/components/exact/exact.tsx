import clsx from "clsx";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import type { ObsStatus } from "../../api/types";
import { deviation, formatRange, formatShare, formatWithUnit, type ValueLike } from "../../lib/format";
import { STATUS_COLOR, StatusIcon, isAbnormal } from "../insights/StatusMark";

/**
 * Exact wording for a result, used everywhere a number is summarised: never "2 of 3 out of range", always the
 * value, its unit, the lab's range and how far outside it is.
 */
export function useExact() {
  const { t } = useTranslation();
  /** "42 % above the upper limit 1.30", or "within 0.60 – 1.30". */
  const describe = (v: ValueLike): string => {
    const d = deviation(v);
    if (d) return t(`exact.${d.side}`, { pct: formatShare(d.fraction), bound: d.bound });
    const range = formatRange(v.ref_low, v.ref_high);
    return range ? t("exact.within", { range }) : t("exact.no_range");
  };
  /** "Creatinine 1.85 mg/dL, 42 % above the upper limit 1.30". */
  const line = (v: ValueLike, short = false): string =>
    `${short ? v.short_name : v.test_name} ${formatWithUnit(v)}, ${describe(v)}`;
  return { describe, line };
}

const TONE: Record<string, string> = {
  low: "text-abnormal border-abnormal/40",
  high: "text-abnormal border-abnormal/40",
  critical_low: "text-critical border-critical/60 font-semibold",
  critical_high: "text-critical border-critical/60 font-semibold",
  normal: "text-normal border-normal/40",
  unknown: "text-muted border-hairline",
};

/** A compact chip: icon, short name, value and unit, e.g. "↑ HbA1c 7.6 %". The full sentence is its label. */
export function ValueChip({ value, to, className }: { value: ValueLike; to?: string; className?: string }) {
  const { line } = useExact();
  const body = (
    <>
      <StatusIcon status={value.status as ObsStatus} />
      <span>{value.short_name}</span>
      <span className="tabular font-medium">{formatWithUnit(value)}</span>
    </>
  );
  const cls = clsx("inline-flex items-center gap-1 rounded-full border bg-raised px-2 py-0.5 text-sm no-underline",
    TONE[value.status] ?? TONE.unknown, className);
  return to ? (
    <Link to={to} className={clsx(cls, "hover:border-ink/40")} title={line(value)} aria-label={line(value)}>{body}</Link>
  ) : (
    <span className={cls} title={line(value)} aria-label={line(value)}>{body}</span>
  );
}

/** A list of chips with "+3 more" folded behind a count; the chips name the worst results first. */
export function ValueChips({ values, max = 4, linkTo }: {
  values: ValueLike[];
  max?: number;
  linkTo?: (v: ValueLike) => string;
}) {
  const { t } = useTranslation();
  if (values.length === 0) return null;
  const shown = values.slice(0, max);
  return (
    <ul className="flex flex-wrap items-center gap-1.5">
      {shown.map((v) => <li key={v.test_code}><ValueChip value={v} to={linkTo?.(v)} /></li>)}
      {values.length > max && <li className="text-sm text-muted">{t("exact.more", { count: values.length - max })}</li>}
    </ul>
  );
}

/**
 * The line under an organ system in the body-map list: the worst result exactly, or, when all are in range, the
 * first values themselves.
 */
export function useOrganNote() {
  const { t } = useTranslation();
  const { line } = useExact();
  return (results: ValueLike[]): string => {
    const out = results.filter((r) => isAbnormal(r.status as ObsStatus));
    if (out.length > 0) {
      const worst = line(out[0], true);
      return out.length > 1 ? `${worst} ${t("exact.and_more_out", { count: out.length - 1 })}` : worst;
    }
    const some = results.slice(0, 2).map((r) => `${r.short_name} ${formatWithUnit(r)}`).join(", ");
    return t("exact.all_in_range", { count: results.length, values: some });
  };
}

export const statusColour = (s: string) => STATUS_COLOR[s as ObsStatus] ?? STATUS_COLOR.unknown;
