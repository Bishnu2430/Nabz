import clsx from "clsx";
import { useRef, useState, type DragEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { useProfiles, useUpload } from "../api/hooks";
import { ReportProgress } from "../components/ReportProgress";
import { Button, ErrorNote, PageTitle } from "../components/ui";

const ACCEPT = "application/pdf,image/jpeg,image/png,image/webp";
const MAX_BYTES = 10 * 1024 * 1024; // mirrors backend/app/services/ingest.py

export default function Upload() {
  const { id = "" } = useParams();
  const { t } = useTranslation();
  const profile = useProfiles().data?.find((p) => p.id === id);
  const upload = useUpload(id);
  const [reportId, setReportId] = useState<string>();
  const [localError, setLocalError] = useState<string>();
  const [dragging, setDragging] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const cameraInput = useRef<HTMLInputElement>(null);

  const send = (file: File | undefined) => {
    if (!file) return;
    setLocalError(undefined);
    if (file.size > MAX_BYTES) {
      setLocalError(t("upload.too_large"));
      return;
    }
    upload.mutate(file, { onSuccess: (r) => setReportId(r.report_id) });
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    send(e.dataTransfer.files[0]);
  };

  const duplicateId =
    upload.error instanceof ApiError && upload.error.status === 409 ? String(upload.error.body.report_id ?? "") : "";

  return (
    <div className="mx-auto max-w-2xl">
      <Link to={`/p/${id}`} className="text-link">← {profile?.display_name ?? t("common.back")}</Link>
      <PageTitle title={t("upload.title")} subtitle={t("upload.hint")} />

      {reportId || upload.isPending ? (
        <ReportProgress reportId={reportId} sending={upload.isPending}
          onRetry={() => { setReportId(undefined); upload.reset(); }} />
      ) : (
        <>
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            className={clsx(
              "flex flex-col items-center gap-4 rounded-lg border-2 border-dashed px-6 py-14 text-center transition",
              dragging ? "border-accent bg-accent/5" : "border-hairline bg-raised",
            )}
          >
            <svg aria-hidden="true" width="44" height="44" viewBox="0 0 48 48" className="text-muted">
              <path d="M12 6h17l9 9v27H12z M29 6v9h9" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinejoin="round" />
              <path d="M18 27h14M18 33h10M18 21h6" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
            </svg>
            <p className="text-muted">{t("upload.drop")}</p>
            <div className="flex flex-wrap justify-center gap-3">
              <Button variant="primary" onClick={() => fileInput.current?.click()}>{t("upload.choose")}</Button>
              <Button onClick={() => cameraInput.current?.click()} className="sm:hidden">{t("upload.camera")}</Button>
            </div>
            <input ref={fileInput} type="file" accept={ACCEPT} className="sr-only" tabIndex={-1} aria-hidden="true"
              data-testid="file-input" onChange={(e) => send(e.target.files?.[0])} />
            <input ref={cameraInput} type="file" accept="image/*" capture="environment" className="sr-only"
              tabIndex={-1} aria-hidden="true" onChange={(e) => send(e.target.files?.[0])} />
          </div>

          <div className="mt-4 space-y-3">
            {localError && <p role="alert" className="text-abnormal">{localError}</p>}
            {duplicateId ? (
              <p role="alert" className="rounded-md border border-borderline/40 bg-borderline/5 px-4 py-3">
                {t("upload.duplicate")}{" "}
                <Link to={`/r/${duplicateId}/review`} className="text-link">{t("upload.open_existing")}</Link>
              </p>
            ) : (
              upload.isError && <ErrorNote error={upload.error} />
            )}
          </div>
        </>
      )}
    </div>
  );
}
