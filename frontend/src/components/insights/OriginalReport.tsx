import { useTranslation } from "react-i18next";

import { useReport } from "../../api/hooks";
import { PageViewer } from "../review/PageViewer";

/**
 * The report itself beside its explanation: the pages as uploaded, each value Nabz read outlined, and the result
 * being read highlighted on the page. The original file opens in a new tab.
 */
export function OriginalReport({ reportId, activeTest, onActiveTest }: {
  reportId: string;
  activeTest: string | null;
  onActiveTest: (code: string | null) => void;
}) {
  const { t } = useTranslation();
  const report = useReport(reportId).data;
  if (!report || report.pages.length === 0) return null;
  const rows = report.observations.map((o) => ({ ...o, needs_attention: false })); // confirmed: nothing left to check
  const active = activeTest ? rows.find((o) => o.test_code === activeTest)?.id : undefined;

  return (
    <section aria-labelledby="original-h">
      <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="original-h" className="font-display text-xl font-bold">{t("original.title")}</h2>
        <a href={`/v1/reports/${reportId}/file`} target="_blank" rel="noreferrer" className="text-sm text-link">
          {t("original.open")} ↗
        </a>
      </div>
      <PageViewer reportId={reportId} pages={report.pages} rows={rows} activeId={active}
        onSelect={(id) => onActiveTest(rows.find((o) => o.id === id)?.test_code ?? null)} />
      <p className="mt-2 text-sm text-muted">{t("original.hint")}</p>
    </section>
  );
}
