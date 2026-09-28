import clsx from "clsx";
import { useTranslation } from "react-i18next";

import type { ObsStatus } from "../../api/types";

export const STATUS_COLOR: Record<ObsStatus, string> = {
  normal: "var(--normal)",
  low: "var(--abnormal)",
  high: "var(--abnormal)",
  critical_low: "var(--critical)",
  critical_high: "var(--critical)",
  unknown: "var(--ink-muted)",
};

const TONE: Record<ObsStatus, string> = {
  normal: "text-normal",
  low: "text-abnormal",
  high: "text-abnormal",
  critical_low: "text-critical font-semibold",
  critical_high: "text-critical font-semibold",
  unknown: "text-muted",
};

export const isAbnormal = (s: ObsStatus) => s !== "normal" && s !== "unknown";

/** Colour + icon + word, never colour alone (doc 12 §5.1). */
export function StatusMark({ status, className }: { status: ObsStatus; className?: string }) {
  const { t } = useTranslation();
  return (
    <span className={clsx("inline-flex items-center gap-1 whitespace-nowrap text-sm", TONE[status], className)}>
      <StatusIcon status={status} />
      {t(`result_status.${status}`)}
    </span>
  );
}

export function StatusIcon({ status }: { status: ObsStatus }) {
  const common = { width: 14, height: 14, viewBox: "0 0 16 16", "aria-hidden": true, fill: "none",
    stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  switch (status) {
    case "normal":
      return <svg {...common}><path d="M3.5 8.5l3 3 6-7" /></svg>;
    case "low":
      return <svg {...common}><path d="M8 3v10M4 9l4 4 4-4" /></svg>;
    case "high":
      return <svg {...common}><path d="M8 13V3M4 7l4-4 4 4" /></svg>;
    case "critical_low":
    case "critical_high":
      // the seal: a square stamp with an exclamation mark
      return (
        <svg {...common}>
          <rect x="1.5" y="1.5" width="13" height="13" rx="2.5" fill="currentColor" stroke="none" />
          <path d="M8 4.5v4.5M8 11.6v.2" stroke="var(--surface-raised)" strokeWidth="2" />
        </svg>
      );
    default:
      return <svg {...common}><path d="M4 8h8" /></svg>;
  }
}
