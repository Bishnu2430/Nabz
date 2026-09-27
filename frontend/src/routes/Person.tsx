import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { useProfiles, useReports } from "../api/hooks";
import type { ReportSummary } from "../api/types";
import { StatusBadge } from "../components/Badges";
import { Card, EmptyState, ErrorNote, Loading, PageTitle } from "../components/ui";
import { formatDate } from "../lib/format";
import NotFound from "./NotFound";

export default function Person() {
  const { id = "" } = useParams();
  const { t } = useTranslation();
  const profiles = useProfiles();
  const reports = useReports(id);

  if (profiles.isPending || reports.isPending) return <Loading />;
  if (profiles.isError) return <ErrorNote error={profiles.error} />;
  const profile = profiles.data.find((p) => p.id === id);
  if (!profile) return <NotFound />;
  if (reports.isError) return <ErrorNote error={reports.error} onRetry={() => void reports.refetch()} />;

  const upload = (
    <Link to={`/p/${id}/upload`} className="inline-flex items-center rounded-md bg-accent px-4 py-2 font-medium text-accent-ink no-underline hover:brightness-110">
      {t("person.upload")}
    </Link>
  );

  return (
    <>
      <Link to="/home" className="text-link">← {t("nav.family")}</Link>
      <PageTitle title={profile.display_name} action={reports.data.length > 0 && upload} />
      {reports.data.length === 0 ? (
        <EmptyState title={t("person.empty_title")} body={t("person.empty_body")} action={upload} />
      ) : (
        <section aria-labelledby="reports-h">
          <h2 id="reports-h" className="mb-4 font-display text-xl font-bold">{t("person.reports")}</h2>
          <ul className="space-y-3">
            {reports.data.map((r) => <li key={r.id}><ReportRow report={r} /></li>)}
          </ul>
        </section>
      )}
    </>
  );
}

function ReportRow({ report }: { report: ReportSummary }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  return (
    <Link to={`/r/${report.id}/review`} className="group block no-underline">
      <Card className="flex flex-wrap items-center gap-x-6 gap-y-2 px-5 py-4 transition group-hover:border-ink/40">
        <div className="min-w-40">
          <p className="font-medium">
            {report.collected_at ? formatDate(report.collected_at, lang) : t("person.undated")}
          </p>
          <p className="text-sm text-muted">{report.lab_name ?? formatDate(report.created_at, lang)}</p>
        </div>
        <p className="text-muted tabular">{t("person.values", { count: report.rows })}</p>
        <div className="ml-auto"><StatusBadge status={report.status} /></div>
      </Card>
    </Link>
  );
}
