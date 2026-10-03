import { useState } from "react";
import { Modal } from "../components/Modal";
import { ProfileForm } from "../components/ProfileForm";
import { useToast } from "../components/Toast";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { useBodyMap, useProfiles, useReports, useWatch } from "../api/hooks";
import type { ReportSummary, ResultBrief, Watch } from "../api/types";
import { StatusBadge } from "../components/Badges";
import { BodyTimeline } from "../components/body/BodyTimeline";
import { Reminders } from "../components/care/Reminders";
import type { OrganCode } from "../components/body/organs";
import { ValueChips } from "../components/exact/exact";
import { OtherRecords } from "../components/records/OtherRecords";
import { useSpan } from "../components/insights/ResultRow";
import { StatusMark } from "../components/insights/StatusMark";
import { PrivacyChoices } from "../components/PrivacyChoices";
import { Icon, type IconName } from "../components/icons";
import { BrushRule, Card, EmptyState, ErrorNote, Loading, PageTitle, PersonSeal, SectionTitle } from "../components/ui";
import { formatDate, formatPercent, formatUnit, formatValue } from "../lib/format";
import NotFound from "./NotFound";

export default function Person() {
  const { id = "" } = useParams();
  const { t, i18n } = useTranslation();
  const profiles = useProfiles();
  const reports = useReports(id);
  const frames = useBodyMap(id).data ?? [];
  const [organ, setOrgan] = useState<OrganCode | null>(null);
  const [editing, setEditing] = useState(false);
  const toast = useToast();

  if (profiles.isPending || reports.isPending) return <Loading />;
  if (profiles.isError) return <ErrorNote error={profiles.error} />;
  const profile = profiles.data.find((p) => p.id === id);
  if (!profile) return <NotFound />;
  if (reports.isError) return <ErrorNote error={reports.error} onRetry={() => void reports.refetch()} />;

  const upload = (
    <Link to={`/p/${id}/upload`} className="btn btn-primary inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2 font-medium text-accent-ink no-underline hover:brightness-110">
      <Icon name="upload" size={18} />
      {t("person.upload")}
    </Link>
  );

  return (
    <>
      <Link to="/home" className="text-link">← {t("nav.family")}</Link>
      <PageTitle title={profile.display_name} mark={<PersonSeal name={profile.display_name} large />}
        subtitle={[t(`profile_form.rel_${profile.relationship}`), t("home.reports", { count: profile.reports }),
          profile.last_tested && t("home.last_tested", { date: formatDate(profile.last_tested, i18n.resolvedLanguage ?? "en") })]
          .filter(Boolean).join(" · ")}
        action={<div className="flex flex-wrap items-center gap-3">
          <button type="button" onClick={() => setEditing(true)}
            className="btn inline-flex items-center gap-1.5 rounded-md border border-hairline bg-raised px-3 py-2 text-sm hover:border-ink/40">
            <Icon name="pen" size={16} />{t("person.edit")}
          </button>
          {reports.data.length > 0 && upload}
        </div>} />
      {editing && (
        <Modal title={t("profile_form.edit_title", { name: profile.display_name })} onClose={() => setEditing(false)}>
          <ProfileForm profile={profile} onCancel={() => setEditing(false)}
            onCreated={() => { setEditing(false); toast(t("toast.profile_saved")); }} />
        </Modal>
      )}
      <nav aria-label={t("person.tools")} className="-mt-4 mb-8 flex flex-wrap gap-2">
        {reports.data.length > 0 && (
          <Link to={`/p/${id}/story`}
            className="btn inline-flex items-center gap-1.5 rounded-full border border-accent bg-accent px-3 py-1 text-sm font-medium text-accent-ink no-underline hover:brightness-110">
            <Icon name="play" size={15} />
            {t("person.story")}
          </Link>
        )}
        {[...(reports.data.length > 0 ? TOOLS : []), ...CARE_TOOLS].map(([path, key, icon]) => (
          <Link key={path} to={`/p/${id}/${path}`}
            className="btn inline-flex items-center gap-1.5 rounded-full border border-hairline bg-raised px-3 py-1 text-sm no-underline hover:border-ink/40">
            <Icon name={icon} size={15} className="text-muted" />
            {t(key)}
          </Link>
        ))}
      </nav>
      {reports.data.length === 0 ? (
        <>
          <EmptyState title={t("person.empty_title")} body={t("person.empty_body")} action={upload} />
          <Reminders profileId={id} />
        </>
      ) : (
        <>
        <BodyTimeline profileId={id} organ={organ} onOrgan={setOrgan} />
        <BrushRule />
        <WatchList profileId={id} />
        <Reminders profileId={id} />
        <section aria-labelledby="reports-h">
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <SectionTitle id="reports-h" icon="report" title={t("person.reports")} className="mb-0" />
            {organ && (
              <p className="text-sm">
                <span className="rounded-full bg-sunken px-3 py-1">{t("organ.showing", { organ: t(`organs.${organ}`) })}</span>{" "}
                <button type="button" className="text-link hover:underline" onClick={() => setOrgan(null)}>
                  {t("organ.show_all")}
                </button>
              </p>
            )}
          </div>
          <ul className="stagger space-y-3">
            {reports.data.map((r) => {
              if (!organ) return <li key={r.id}><ReportRow report={r} profileId={id} /></li>;
              const tests = frames.find((f) => f.report_id === r.id)?.organs.find((o) => o.code === organ)?.tests;
              return tests ? <li key={r.id}><ReportRow report={r} profileId={id} values={tests} /></li> : null;
            })}
          </ul>
        </section>
        <OtherRecords profileId={id} />
        </>
      )}
      <PrivacyChoices profileId={id} />
    </>
  );
}

const TOOLS: [string, string, IconName][] = [
  ["tests", "person.all_tests", "tests"], ["summary", "person.summary", "summary"], ["compare", "person.compare", "compare"]];
// kept by the family themselves, so they are there before the first report
const CARE_TOOLS: [string, string, IconName][] = [["readings", "person.readings", "readings"], ["card", "person.card", "card"]];

const ANALYSED = new Set(["verified", "analysing", "explaining", "explained"]);

function WatchList({ profileId }: { profileId: string }) {
  const { t, i18n } = useTranslation();
  const watch = useWatch(profileId);
  const span = useSpan();
  if (!watch.data?.length) return null;
  const lang = i18n.resolvedLanguage ?? "en";
  return (
    <section aria-labelledby="watch-h" className="mb-10">
      <SectionTitle id="watch-h" icon="trend" title={t("person.watch")} className="mb-4" />
      <ul className="stagger grid gap-3 sm:grid-cols-2">
        {watch.data.map((w: Watch) => (
          <li key={w.test_code}>
            <Link to={`/p/${profileId}/tests/${w.test_code}`} className="group block no-underline">
              <Card className="lift corner-pattern h-full px-5 py-4 group-hover:border-ink/40">
                <div className="flex items-baseline justify-between gap-3">
                  <span className="font-medium">{w.test_name}</span>
                  <StatusMark status={w.latest.status} />
                </div>
                <p className="tabular mt-1 text-lg">
                  {formatValue(w.latest.value, w.latest.decimals)} <span className="text-sm text-muted">{formatUnit(w.latest.unit)}</span>
                </p>
                <p className="text-sm text-muted">
                  {w.confirmed && w.latest.trend
                    ? t(w.direction === "rising" ? "insights.trend_rising" : "insights.trend_falling",
                      { span: span(w.latest.trend.first, w.latest.trend.last) })
                    : w.latest.change?.fraction != null && w.latest.previous
                      ? t("insights.change_since", { change: formatPercent(w.latest.change.fraction),
                        date: formatDate(w.latest.previous.date, lang) })
                      : null}
                </p>
              </Card>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

function ReportRow({ report, profileId, values }: { report: ReportSummary; profileId: string; values?: ResultBrief[] }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const shown = values ?? report.out_of_range ?? [];
  const analysed = ANALYSED.has(report.status);
  return (
    <Card className="lift px-5 py-4">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
        <Link to={analysed ? `/r/${report.id}` : `/r/${report.id}/review`} className="flex min-w-40 items-center gap-3 no-underline">
          <span className="grid size-9 shrink-0 place-items-center rounded-md bg-sunken text-muted"><Icon name="report" size={18} /></span>
          <span>
          <span className="block font-medium text-ink hover:text-link">
            {report.collected_at ? formatDate(report.collected_at, lang) : t("person.undated")}
          </span>
          <span className="block text-sm text-muted">{report.lab_name ?? formatDate(report.created_at, lang)}</span>
          </span>
        </Link>
        <p className="text-muted tabular">{t("person.values", { count: report.rows })}</p>
        <div className="ml-auto"><StatusBadge status={report.status} /></div>
      </div>
      {analysed && (
        <div className="mt-2">
          {shown.length > 0 ? (
            <ValueChips values={shown} max={values ? 12 : 5} linkTo={(v) => `/p/${profileId}/tests/${v.test_code}`} />
          ) : (
            <p className="text-sm text-normal">{t("person.all_in_range", { count: report.rows })}</p>
          )}
        </div>
      )}
      {report.note && <p className="mt-2 text-sm text-muted">“{report.note}”</p>}
    </Card>
  );
}
