import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, Navigate, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { useInsights } from "../api/hooks";
import { StatusBadge } from "../components/Badges";
import { BodyMap } from "../components/body/BodyMap";
import { ExplanationExcerpt } from "../components/body/OrganDetail";
import { OrganPanel } from "../components/body/OrganPanel";
import { isOrganCode, type OrganCode } from "../components/body/organs";
import { Enso } from "../components/Enso";
import { useOrganNote, ValueChips } from "../components/exact/exact";
import { CriticalBanner } from "../components/insights/CriticalBanner";
import { ExplanationCard } from "../components/insights/ExplanationCard";
import { OrganCard } from "../components/insights/OrganCard";
import { OriginalReport } from "../components/insights/OriginalReport";
import { ReportNote } from "../components/insights/ReportNote";
import { isAbnormal } from "../components/insights/StatusMark";
import { ErrorNote, Loading } from "../components/ui";
import { deviation, formatDate } from "../lib/format";
import NotFound from "./NotFound";

const NOT_CONFIRMED = new Set(["uploaded", "queued", "processing", "needs_review", "failed", "rejected"]);
const SEVERITY: Record<string, number> = { critical_low: 3, critical_high: 3, low: 2, high: 2, normal: 1, unknown: 0 };

export default function Insights() {
  const { id = "" } = useParams();
  const { t, i18n } = useTranslation();
  const insights = useInsights(id);
  const [organ, setOrgan] = useState<OrganCode | null>(null);
  const [activeTest, setActiveTest] = useState<string | null>(null);
  const organNote = useOrganNote();

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
  const outside = all.filter((r) => isAbnormal(r.status))
    .sort((a, b) => SEVERITY[b.status] - SEVERITY[a.status] || (deviation(b)?.fraction ?? 0) - (deviation(a)?.fraction ?? 0));
  const lang = i18n.resolvedLanguage ?? "en";
  const chosen = data.organs.find((o) => o.code === organ);
  const name = (o: { names: Record<string, string> }) => o.names[lang] ?? o.names.en;
  const shownOrgans = chosen ? [chosen] : data.organs;

  return (
    <>
      <Link to={`/p/${data.person.id}`} className="text-link">← {data.person.display_name}</Link>
      <div className="mb-4 mt-2 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold sm:text-4xl">{t("insights.title")}</h1>
          <p className="mt-1 text-muted">
            {[data.report.lab_name, data.report.collected_at && formatDate(data.report.collected_at, lang)]
              .filter(Boolean).join(" · ")}
          </p>
        </div>
        <StatusBadge status={data.report.status} />
      </div>

      <ReportNote reportId={id} profileId={data.person.id} note={data.report.note ?? null} />

      <CriticalBanner results={data.critical} />

      <div className="mb-6">
        <p className="text-lg">
          {outside.length > 0
            ? t("insights.outside", { count: outside.length, total: all.length })
            : t("insights.all_in_range", { total: all.length })}
        </p>
        {outside.length > 0 && (
          <div className="mt-2">
            <ValueChips values={outside} max={10} linkTo={(v) => `/p/${data.person.id}/tests/${v.test_code}`} />
          </div>
        )}
      </div>

      <BodyMap
        items={data.organs.filter((o) => isOrganCode(o.code)).map((o) => ({
          code: o.code as OrganCode,
          status: o.status,
          name: name(o),
          note: organNote(o.results),
        }))}
        selected={organ}
        onSelect={setOrgan}
        detail={chosen && (
          <OrganPanel profileId={data.person.id} organ={chosen.code as OrganCode} name={name(chosen)} reportId={id}
            onBack={() => setOrgan(null)} extra={<ExplanationExcerpt organ={chosen} reportId={id} />} />
        )}
      />

      <div className="mb-4 flex flex-wrap items-baseline gap-3">
        <h2 className="font-display text-2xl font-bold">{t("insights.all_results")}</h2>
        {chosen && (
          <p className="text-sm">
            <span className="rounded-full bg-sunken px-3 py-1">{t("organ.showing", { organ: name(chosen) })}</span>{" "}
            <button type="button" className="text-link hover:underline" onClick={() => setOrgan(null)}>
              {t("organ.show_all")}
            </button>
          </p>
        )}
      </div>
      <div className="stagger grid gap-5 lg:grid-cols-2">
        {shownOrgans.map((o) => <OrganCard key={o.code} organ={o} profileId={data.person.id} />)}
      </div>

      {/* the explanation and the report it explains, side by side */}
      <div id="explanation" className="mt-10 grid scroll-mt-6 gap-6 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
        <ExplanationCard reportId={id} profileId={data.person.id} results={all} activeTest={activeTest}
          onActiveTest={setActiveTest} />
        <div className="lg:sticky lg:top-20 lg:self-start">
          <OriginalReport reportId={id} activeTest={activeTest} onActiveTest={setActiveTest} />
        </div>
      </div>

      <p className="mt-6">
        <Link to={`/r/${id}/review`} className="text-link">{t("insights.values_as_read")}</Link>
      </p>
    </>
  );
}
