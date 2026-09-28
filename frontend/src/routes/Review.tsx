import { useMemo, useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { IN_PROGRESS, useAddObservation, useConfirm, useReport, useReportStatus } from "../api/hooks";
import type { Observation, Report } from "../api/types";
import { AttentionMark, StatusBadge } from "../components/Badges";
import { Enso } from "../components/Enso";
import { HankoSeal } from "../components/HankoSeal";
import { PageViewer } from "../components/review/PageViewer";
import { TestPicker } from "../components/review/TestPicker";
import { Field, ValueRow } from "../components/review/ValueRow";
import { Button, Card, ErrorNote, Loading, fieldClass } from "../components/ui";
import { formatDate } from "../lib/format";
import NotFound from "./NotFound";

export default function Review() {
  const { id = "" } = useParams();
  const { t } = useTranslation();
  const report = useReport(id);
  useReportStatus(report.data && IN_PROGRESS.has(report.data.status) ? id : undefined);

  if (report.isPending) return <Loading />;
  if (report.isError) {
    if (report.error instanceof ApiError && report.error.status === 404) return <NotFound />;
    return <ErrorNote error={report.error} onRetry={() => void report.refetch()} />;
  }
  const r = report.data;
  if (IN_PROGRESS.has(r.status)) {
    return (
      <div className="py-16 text-center">
        <Enso label={r.status === "processing" ? t("upload.reading") : t("upload.queued")} size={140} />
      </div>
    );
  }
  if (r.status === "failed" || r.status === "rejected") {
    return (
      <div className="mx-auto max-w-xl py-12">
        <p role="alert" className="text-abnormal">{t("upload.failed")}</p>
        <Link to={`/p/${r.profile_id}/upload`} className="mt-4 inline-block text-link">{t("upload.title")}</Link>
      </div>
    );
  }
  return <ReviewBody report={r} />;
}

/** Rows the model is least sure about come first. The order is fixed on first load so rows don't jump while edited. */
function useStableOrder(rows: Observation[]): Observation[] {
  const order = useRef<string[] | null>(null);
  if (order.current === null) {
    const weakest = rows.filter((o) => o.needs_attention).sort((a, b) => a.confidence - b.confidence);
    const rest = rows.filter((o) => !o.needs_attention);
    order.current = [...weakest, ...rest].map((o) => o.id);
  }
  const rank = new Map(order.current.map((id, i) => [id, i]));
  return [...rows].sort((a, b) => (rank.get(a.id) ?? Infinity) - (rank.get(b.id) ?? Infinity));
}

function ReviewBody({ report }: { report: Report }) {
  const { t, i18n } = useTranslation();
  const rows = useStableOrder(report.observations);
  const [activeId, setActiveId] = useState<string>();
  const editable = report.status === "needs_review";

  const select = (id: string) => {
    setActiveId(id);
  };
  const selectFromPage = (id: string) => {
    setActiveId(id);
    document.getElementById(`row-${id}`)?.scrollIntoView?.({ block: "center", behavior: "smooth" });
  };

  return (
    <>
      <Link to={`/p/${report.profile_id}`} className="text-link">← {t("common.back")}</Link>
      <div className="mb-6 mt-2 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold sm:text-4xl">{t("review.title")}</h1>
          <p className="mt-1 text-muted">
            {[report.lab_name, report.collected_at && formatDate(report.collected_at, i18n.resolvedLanguage ?? "en")]
              .filter(Boolean)
              .join(" · ")}
          </p>
        </div>
        <StatusBadge status={report.status} />
      </div>

      {editable && <p className="mb-6 max-w-prose">{t("review.intro")}</p>}

      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,28rem)]">
        <div className="lg:sticky lg:top-4 lg:self-start">
          <PageViewer reportId={report.id} pages={report.pages} rows={rows} activeId={activeId} onSelect={selectFromPage} />
        </div>

        <div>
          <p className="mb-4" aria-live="polite">
            {report.needs_attention > 0 ? (
              <AttentionMark label={t("review.attention", { count: report.needs_attention })} />
            ) : (
              <span className="text-normal">✓ {t("review.all_good")}</span>
            )}
          </p>
          <ul className="space-y-3">
            {rows.map((o) => (
              <ValueRow key={o.id} row={o} reportId={report.id} editable={editable} active={o.id === activeId}
                onSelect={() => select(o.id)} />
            ))}
          </ul>
          {editable && <AddRow reportId={report.id} />}
          <ConfirmPanel report={report} />
        </div>
      </div>
    </>
  );
}

function AddRow({ reportId }: { reportId: string }) {
  const { t } = useTranslation();
  const add = useAddObservation(reportId);
  const [open, setOpen] = useState(false);
  const [testCode, setTestCode] = useState<string | null>(null);
  const [value, setValue] = useState("");
  const [unit, setUnit] = useState("");
  const [range, setRange] = useState("");

  const reset = () => {
    setOpen(false);
    setTestCode(null);
    setValue("");
    setUnit("");
    setRange("");
    add.reset();
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!testCode || !value.trim()) return;
    add.mutate(
      { test_code: testCode, raw_value: value.trim(), raw_unit: unit.trim() || undefined, raw_range: range.trim() || undefined },
      { onSuccess: reset },
    );
  };

  if (!open) {
    return (
      <Button variant="quiet" className="mt-4 px-0" onClick={() => setOpen(true)}>+ {t("review.add")}</Button>
    );
  }
  return (
    <Card className="mt-4 p-4">
      <form onSubmit={submit} className="space-y-4">
        <h3 className="font-medium">{t("review.add_title")}</h3>
        <TestPicker value={testCode} candidates={[]} onPick={setTestCode} />
        <div className="grid gap-3 sm:grid-cols-3">
          <Field label={t("review.value")} value={value} onChange={setValue} inputMode="decimal" required />
          <Field label={t("review.unit")} value={unit} onChange={setUnit} />
          <Field label={t("review.range")} value={range} onChange={setRange} />
        </div>
        {add.isError && <ErrorNote error={add.error} />}
        <div className="flex gap-3">
          <Button type="submit" variant="primary" disabled={!testCode || !value.trim() || add.isPending}>
            {t("review.add_button")}
          </Button>
          <Button onClick={reset}>{t("common.cancel")}</Button>
        </div>
      </form>
    </Card>
  );
}

function ConfirmPanel({ report }: { report: Report }) {
  const { t } = useTranslation();
  const confirm = useConfirm(report.id);
  const [collected, setCollected] = useState(report.collected_at ?? "");
  const done = report.status !== "needs_review";
  const blocked = report.unmapped > 0;
  const today = useMemo(() => new Date().toISOString().slice(0, 10), []);

  return (
    <Card className="relative mt-8 overflow-hidden p-6">
      <div className="pointer-events-none absolute -right-2 -top-2">
        <HankoSeal stamped={done} size={112} />
      </div>
      {done ? (
        <div className="pr-24" aria-live="polite">
          <h2 className="font-display text-2xl font-bold">{t("review.confirmed")}</h2>
          <p className="mt-2 text-muted">{t("review.confirmed_body")}</p>
          <Link to={`/r/${report.id}`} className="mt-4 inline-flex rounded-md bg-accent px-4 py-2 font-medium text-accent-ink no-underline hover:brightness-110">
            {t("review.see_results")}
          </Link>
        </div>
      ) : (
        <div className="space-y-4 pr-4">
          <label className="block max-w-60">
            <span className="mb-1 block text-sm text-muted">{t("review.collected")}</span>
            <input type="date" value={collected} max={today} onChange={(e) => setCollected(e.target.value)} className={fieldClass} />
          </label>
          {blocked && <p className="text-borderline">{t("review.blocked")}</p>}
          {confirm.isError && <ErrorNote error={confirm.error} />}
          <Button variant="primary" className="w-full sm:w-auto" disabled={blocked || confirm.isPending}
            onClick={() => confirm.mutate(collected && collected !== report.collected_at ? collected : null)}>
            {confirm.isPending ? t("review.confirming") : t("review.confirm")}
          </Button>
        </div>
      )}
    </Card>
  );
}
