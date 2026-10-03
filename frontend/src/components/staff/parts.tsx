import clsx from "clsx";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import type { Span } from "../../api/staff";
import { Icon, type IconName } from "../icons";

const TONE: Record<string, string> = {
  diagnosis: "bg-abnormal/15 ring-abnormal/50",
  treatment: "bg-abnormal/15 ring-abnormal/50",
  reassurance: "bg-borderline/20 ring-borderline/50",
  instruction: "bg-critical/15 ring-critical/50",
  number: "bg-borderline/20 ring-borderline/50",
  label: "bg-link/15 ring-link/40",
};

/** Text with what each check caught marked, and the check's name on hover and for screen readers. */
export function MarkedText({ text, spans, className }: { text: string; spans: Span[]; className?: string }) {
  const { t } = useTranslation();
  const parts: ReactNode[] = [];
  let at = 0;
  for (const s of spans) {
    if (s.start < at) continue; // overlapping matches: the first one wins
    if (s.start > at) parts.push(text.slice(at, s.start));
    const name = t(`console.code.${s.code}`, s.code);
    parts.push(
      <mark key={`${s.start}-${s.code}`} title={name}
        className={clsx("rounded px-0.5 text-ink ring-1", TONE[s.code] ?? "bg-sunken ring-hairline")}>
        {text.slice(s.start, s.end)}
        <span className="sr-only"> ({name})</span>
      </mark>,
    );
    at = s.end;
  }
  parts.push(text.slice(at));
  return <p className={clsx("whitespace-pre-line", className)}>{parts}</p>;
}

/** The name of a check, as a small chip. */
export function CodeChip({ code }: { code: string }) {
  const { t } = useTranslation();
  return (
    <span className={clsx("inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1",
      TONE[code] ?? "bg-sunken ring-hairline")}>
      {t(`console.code.${code}`, code)}
    </span>
  );
}

/** A row of tabs kept in the URL by the caller. */
export function Tabs<T extends string>({ tabs, value, onChange, label }: {
  tabs: { id: T; label: string; icon: IconName; count?: number }[];
  value: T;
  onChange: (id: T) => void;
  label: string;
}) {
  return (
    <div role="tablist" aria-label={label} className="mb-6 flex flex-wrap gap-1 border-b border-hairline">
      {tabs.map((tab) => (
        <button key={tab.id} type="button" role="tab" aria-selected={tab.id === value} onClick={() => onChange(tab.id)}
          className={clsx("-mb-px inline-flex items-center gap-2 border-b-2 px-3 py-2 text-sm transition-colors",
            tab.id === value ? "border-accent font-medium text-ink" : "border-transparent text-muted hover:text-ink")}>
          <Icon name={tab.icon} size={16} />
          {tab.label}
          {tab.count != null && tab.count > 0 && (
            <span className="tabular rounded-full bg-accent px-1.5 text-xs font-medium text-accent-ink">{tab.count}</span>
          )}
        </button>
      ))}
    </div>
  );
}

/** One number with its label and mark. */
export function StatTile({ icon, label, value, note, tone }: {
  icon: IconName;
  label: string;
  value: ReactNode;
  note?: ReactNode;
  tone?: "good" | "warn";
}) {
  return (
    <div className="card corner-pattern rounded-lg border border-hairline bg-raised px-4 py-3">
      <p className="flex items-center gap-2 text-sm text-muted"><Icon name={icon} size={16} />{label}</p>
      <p className={clsx("tabular mt-1 text-2xl font-semibold", tone === "good" && "text-normal", tone === "warn" && "text-abnormal")}>
        {value}
      </p>
      {note && <p className="text-xs text-muted">{note}</p>}
    </div>
  );
}

/** A yes/no light for system health: never colour alone. */
export function Light({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className={clsx("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-sm",
      ok ? "border-normal/40 text-normal" : "border-abnormal/40 text-abnormal")}>
      <Icon name={ok ? "check" : "alert"} size={14} />
      {label}
    </span>
  );
}
