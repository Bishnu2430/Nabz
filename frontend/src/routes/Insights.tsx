import { useTranslation } from "react-i18next";
import { Link, Navigate, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { useInsights } from "../api/hooks";
import { StatusBadge } from "../components/Badges";
import { Enso } from "../components/Enso";
import { CriticalBanner } from "../components/insights/CriticalBanner";
import { ExplanationCard } from "../components/insights/ExplanationCard";
import { OrganCard } from "../components/insights/OrganCard";
import { isAbnormal } from "../components/insights/StatusMark";
import { ErrorNote, Loading } from "../components/ui";
import { formatDate } from "../lib/format";
import NotFound from "./NotFound";

const NOT_CONFIRMED = new Set(["uploaded", "queued", "processing", "needs_review", "failed", "rejected"]);

export default function Insights() {
  const { id = "" } = useParams();
  const { t, i18n } = useTranslation();
  const insights = useInsights(id);

  if (insights.isPending) return <Loading />;
  if (insights.isError) {
    if (insights.error instanceof ApiError && insights.error.status === 404) return <NotFound />;
    return <ErrorNote error={insights.error} onRetry={() => void insights.refetch()} />;
  }
  const data = insights.data;
  if (NOT_CONFIRMED.has(data.report.status)) return <Navigate to={`/r/${id}/review`} replace />;
  if (!data.analysed) {
    return <div className="py-16 text-center"><Enso label={t("insights.analysing")} size={140} /></div>;
  }

  const all = data.organs.flatMap((o) => o.results);
  const outside = all.filter((r) => isAbnormal(r.status)).length;
  const lang = i18n.resolvedLanguage ?? "en";

  return (
    <>
      <Link to={`/p/${data.person.id}`} className="text-link">← {data.person.display_name}</Link>
      <div className="mb-6 mt-2 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold sm:text-4xl">{t("insights.title")}</h1>
          <p className="mt-1 text-muted">
            {[data.report.lab_name, data.report.collected_at && formatDate(data.report.collected_at, lang)]
              .filter(Boolean).join(" · ")}
          </p>
        </div>
        <StatusBadge status={data.report.status} />
      </div>

      <CriticalBanner results={data.critical} />

      <p className="mb-6 text-lg">
        {outside > 0
          ? t("insights.outside", { count: outside, total: all.length })
          : t("insights.all_in_range", { total: all.length })}
      </p>

      <div className="grid gap-5 lg:grid-cols-2">
        {data.organs.map((o) => <OrganCard key={o.code} organ={o} profileId={data.person.id} />)}
      </div>

      <div className="mt-8">
        <ExplanationCard reportId={id} profileId={data.person.id} results={all} />
      </div>

      <p className="mt-6">
        <Link to={`/r/${id}/review`} className="text-link">{t("insights.values_as_read")}</Link>
      </p>
    </>
  );
}
