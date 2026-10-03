import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "../../api/client";
import { useAddNote, useClinicianReport } from "../../api/clinicians";
import { SharedReportView } from "../../components/shared/SharedReportView";
import { useToast } from "../../components/Toast";
import { Button, Card, EmptyState, ErrorNote, Loading, SectionTitle, fieldClass } from "../../components/ui";
import { formatDateTime } from "../../lib/format";

/**
 * One report a family shared with this doctor: the same read-only view as a share link, with the doctor's notes
 * and a place to add one. The family sees the notes beside the report.
 */
export default function ClinicianReport() {
  const { id = "" } = useParams();
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const report = useClinicianReport(id);
  const add = useAddNote(id);
  const toast = useToast();
  const [text, setText] = useState("");

  if (report.isPending) return <Loading />;
  if (report.isError) {
    const gone = report.error instanceof ApiError && report.error.status === 404;
    return gone ? <EmptyState title={t("clinician.gone_title")} body={t("clinician.gone_body")}
      action={<Link to="/clinician" className="text-link">{t("clinician.back")}</Link>} />
      : <ErrorNote error={report.error} onRetry={() => void report.refetch()} />;
  }
  const d = report.data;

  return (
    <article className="mx-auto max-w-4xl">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3 print:hidden">
        <Link to="/clinician" className="text-link">← {t("clinician.back")}</Link>
        <Button onClick={() => window.print()}>{t("summary.print")}</Button>
      </div>
      <SharedReportView d={d} />

      <section className="mt-10 print:hidden" aria-labelledby="cl-notes-h">
        <SectionTitle id="cl-notes-h" icon="pen" title={t("clinician.notes")} />
        <p className="mb-3 max-w-prose text-sm text-muted">{t("clinician.notes_intro")}</p>
        {d.notes.length > 0 && (
          <Card className="mb-4 divide-y divide-hairline">
            {d.notes.map((n) => (
              <figure key={n.id} className="px-4 py-3">
                <blockquote className="whitespace-pre-line">{n.text}</blockquote>
                <figcaption className="mt-1 text-sm text-muted">
                  {[n.clinician_name, formatDateTime(n.created_at, lang)].filter(Boolean).join(" · ")}
                </figcaption>
              </figure>
            ))}
          </Card>
        )}
        <form onSubmit={(e) => {
          e.preventDefault();
          add.mutate(text.trim(), { onSuccess: () => { setText(""); toast(t("clinician.note_added")); } });
        }}>
          <label htmlFor="cl-note" className="mb-1 block font-medium">{t("clinician.add_note")}</label>
          <textarea id="cl-note" value={text} onChange={(e) => setText(e.target.value)} rows={3} maxLength={2000}
            className={fieldClass} placeholder={t("clinician.note_placeholder")} />
          {add.isError && <div className="mt-2"><ErrorNote error={add.error} /></div>}
          <Button type="submit" variant="primary" className="mt-2" disabled={add.isPending || !text.trim()}>
            {t("clinician.send_note")}
          </Button>
        </form>
      </section>
    </article>
  );
}
