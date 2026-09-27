import clsx from "clsx";
import { useTranslation } from "react-i18next";

import type { ReportStatus } from "../api/types";
import type { Position } from "../lib/format";

const STATUS_TONE: Record<ReportStatus, string> = {
  uploaded: "text-muted border-hairline",
  queued: "text-muted border-hairline",
  processing: "text-link border-link/40",
  needs_review: "text-borderline border-borderline/50",
  verified: "text-normal border-normal/50",
  analysing: "text-link border-link/40",
  explaining: "text-link border-link/40",
  explained: "text-normal border-normal/50",
  failed: "text-abnormal border-abnormal/50",
  rejected: "text-abnormal border-abnormal/50",
  deleted: "text-muted border-hairline",
};

export function StatusBadge({ status }: { status: ReportStatus }) {
  const { t } = useTranslation();
  return (
    <span className={clsx("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-sm", STATUS_TONE[status])}>
      <span aria-hidden="true" className="size-1.5 rounded-full bg-current" />
      {t(`status.${status}`)}
    </span>
  );
}

/** Colour + icon + word, never colour alone (doc 12 §5.1). */
export function PositionMark({ position }: { position: Position }) {
  const { t } = useTranslation();
  if (position === "unknown") return null;
  const map = {
    low: { icon: "↓", tone: "text-abnormal" },
    high: { icon: "↑", tone: "text-abnormal" },
    normal: { icon: "•", tone: "text-normal" },
  } as const;
  const m = map[position];
  return (
    <span className={clsx("inline-flex items-center gap-1 text-sm", m.tone)}>
      <span aria-hidden="true">{m.icon}</span>
      {t(`position.${position}`)}
    </span>
  );
}

/** Shown on rows the confidence model is unsure about: a brush-stroke underline and the word. */
export function AttentionMark({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center gap-1 text-sm font-medium text-borderline">
      <svg aria-hidden="true" width="14" height="14" viewBox="0 0 16 16">
        <path d="M8 1.5 15 14H1z" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
        <path d="M8 6v4M8 11.8v.4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      </svg>
      {label}
    </span>
  );
}
