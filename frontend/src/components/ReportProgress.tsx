import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { useReport, useReportStatus } from "../api/hooks";
import { Enso } from "./Enso";
import { Button, Card } from "./ui";

/**
 * A report on its way to the review screen: the brush circle turns while it is sent, waits and is read, then the
 * page moves on to "check the values". Used after an upload and after choosing the sample report.
 */
export function ReportProgress({ reportId, sending, onRetry }: { reportId?: string; sending: boolean; onRetry: () => void }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const live = useReportStatus(reportId);
  const polled = useReport(reportId ?? "", Boolean(reportId)).data?.status; // if the event stream drops
  const status = live ?? polled;

  useEffect(() => {
    if (status === "needs_review" && reportId) {
      const timer = setTimeout(() => navigate(`/r/${reportId}/review`), 900);
      return () => clearTimeout(timer);
    }
  }, [status, reportId, navigate]);

  const working = sending || (reportId && status !== "needs_review" && status !== "failed");
  const phase = sending
    ? t("upload.uploading")
    : status === "processing"
      ? t("upload.reading")
      : status === "needs_review"
        ? t("upload.ready")
        : t("upload.queued");

  return (
    <Card className="flex flex-col items-center gap-4 px-6 py-12 text-center">
      {status === "failed" ? (
        <>
          <p role="alert" className="text-abnormal">{t("upload.failed")}</p>
          <Button onClick={onRetry}>{t("common.retry")}</Button>
        </>
      ) : (
        <Enso active={Boolean(working)} label={phase} size={140} />
      )}
    </Card>
  );
}
