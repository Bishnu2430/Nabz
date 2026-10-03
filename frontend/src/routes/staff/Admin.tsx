import clsx from "clsx";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";

import { useMe, type Role } from "../../api/auth";
import {
  useAdminUsers, useAudit, useJobs, useOverview, useRetryJob, useUserAction, type AuditEntry, type Overview,
} from "../../api/staff";
import { Icon } from "../../components/icons";
import { Light, StatTile, Tabs } from "../../components/staff/parts";
import { useToast } from "../../components/Toast";
import { Button, Card, Empty, ErrorNote, Loading, PageTitle, SectionTitle, fieldClass } from "../../components/ui";
import { formatDate, formatDateTime } from "../../lib/format";

type Tab = "overview" | "users" | "jobs" | "audit";
const ROLES: Role[] = ["user", "clinician", "reviewer", "admin"];

/**
 * Running the system (FR-49): health, counts and activity, the job monitor and the audit log for staff; users and
 * roles for admins. Nothing here shows a name, a value or a report: people appear only as counts.
 */
export default function Admin() {
  const { t } = useTranslation();
  const me = useMe().data;
  const isAdmin = me?.role === "admin";
  const [params, setParams] = useSearchParams();
  const tab = (params.get("tab") as Tab | null) ?? "overview";
  const tabs = [
    { id: "overview" as const, label: t("console.tab_overview"), icon: "trend" as const },
    ...(isAdmin ? [{ id: "users" as const, label: t("console.tab_users"), icon: "family" as const }] : []),
    { id: "jobs" as const, label: t("console.tab_jobs"), icon: "clock" as const },
    { id: "audit" as const, label: t("console.tab_audit"), icon: "book" as const },
  ];
  return (
    <>
      <PageTitle icon="settings" title={t("console.admin_title")} subtitle={t("console.admin_intro")} />
      <Tabs label={t("console.admin_title")} tabs={tabs} value={tab} onChange={(id) => setParams({ tab: id }, { replace: true })} />
      {tab === "overview" && <OverviewTab />}
      {tab === "users" && isAdmin && <UsersTab />}
      {tab === "jobs" && <JobsTab canRetry={isAdmin} />}
      {tab === "audit" && <AuditTab />}
    </>
  );
}

function sum(record: Record<string, number>) {
  return Object.values(record).reduce((a, b) => a + b, 0);
}

function OverviewTab() {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const overview = useOverview();
  if (overview.isPending) return <Loading />;
  if (overview.isError) return <ErrorNote error={overview.error} />;
  const { health, counts, activity } = overview.data;
  const failed = health.jobs.failed ?? 0;
  return (
    <div className="space-y-8">
      <section>
        <SectionTitle icon="shield" title={t("console.health")} />
        <div className="flex flex-wrap gap-2">
          <Light ok={health.database} label={t("console.h_database")} />
          <Light ok={Boolean(health.worker_last_job)} label={health.worker_last_job
            ? t("console.h_worker", { time: formatDateTime(health.worker_last_job, lang) }) : t("console.h_worker_idle")} />
          <Light ok={health.model} label={t("console.h_model")} />
          <Light ok={health.voice} label={t("console.h_voice")} />
          <Light ok={health.embeddings} label={t("console.h_embeddings")} />
          <Light ok={failed === 0} label={t("console.h_failed", { count: failed })} />
          <span className="inline-flex items-center gap-1.5 rounded-full border border-hairline px-2.5 py-1 text-sm text-muted">
            <Icon name="mail" size={14} />{t("console.h_mail", { backend: health.mail })}
          </span>
        </div>
      </section>
      <section>
        <SectionTitle icon="tests" title={t("console.counts")} />
        <div className="stagger grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile icon="family" label={t("console.c_accounts")} value={sum(counts.users)}
            note={t("console.c_accounts_note", { staff: (counts.users.reviewer ?? 0) + (counts.users.admin ?? 0), twoStep: counts.two_step })} />
          <StatTile icon="person" label={t("console.c_people")} value={counts.people} />
          <StatTile icon="report" label={t("console.c_reports")} value={sum(counts.reports)}
            note={t("console.c_reports_note", { count: counts.reports.needs_review ?? 0 })} />
          <StatTile icon="book" label={t("console.c_explanations")} value={sum(counts.explanations)}
            note={t("console.stat_explanations_note", { model: counts.explanations.model ?? 0, template: counts.explanations.template ?? 0 })} />
          <StatTile icon="chat" label={t("console.c_questions")} value={sum(counts.questions)}
            note={t("console.c_questions_note", { count: counts.questions.refusal ?? 0 })} />
          <StatTile icon="share" label={t("console.c_links")} value={counts.share_links} />
          <StatTile icon="readings" label={t("console.c_readings")} value={counts.readings}
            note={t("console.c_reminders", { count: counts.reminders })} />
          <StatTile icon="film" label={t("console.c_records")} value={counts.records}
            note={t("console.c_catalogue", { tests: counts.tests, passages: counts.passages })} />
        </div>
      </section>
      <section>
        <SectionTitle icon="trend" title={t("console.activity")} />
        <Card className="p-5"><ActivityChart activity={activity} /></Card>
      </section>
    </div>
  );
}

const SERIES = [
  { key: "uploads", color: "var(--accent)" },
  { key: "explanations", color: "var(--link)" },
  { key: "questions", color: "var(--normal)" },
] as const;

/** Fourteen days of uploads, explanations and questions as grouped bars; every number is also in the table. */
function ActivityChart({ activity }: { activity: Overview["activity"] }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const max = Math.max(1, ...activity.flatMap((d) => SERIES.map((s) => d[s.key])));
  const H = 140;
  return (
    <figure>
      <div className="mb-3 flex flex-wrap gap-4 text-sm">
        {SERIES.map((s) => (
          <span key={s.key} className="inline-flex items-center gap-1.5">
            <span aria-hidden="true" className="size-2.5 rounded-sm" style={{ background: s.color }} />
            {t(`console.series_${s.key}`)}
            <span className="tabular text-muted">{activity.reduce((a, d) => a + d[s.key], 0)}</span>
          </span>
        ))}
      </div>
      <div className="flex h-40 items-end gap-1.5" role="img" aria-label={t("console.activity_label")}>
        {activity.map((d) => (
          <div key={d.day} className="flex flex-1 flex-col items-center gap-1">
            <div className="flex w-full items-end justify-center gap-px" style={{ height: H }}>
              {SERIES.map((s) => (
                <div key={s.key} className="w-1/3 max-w-3 rounded-t-sm transition-all"
                  title={`${formatDate(d.day, lang)} · ${t(`console.series_${s.key}`)}: ${d[s.key]}`}
                  style={{ height: `${(d[s.key] / max) * 100}%`, minHeight: d[s.key] ? 2 : 0, background: s.color }} />
              ))}
            </div>
            <span className="text-[10px] text-muted">{new Date(`${d.day}T00:00:00Z`).getUTCDate()}</span>
          </div>
        ))}
      </div>
      <figcaption className="mt-2 text-xs text-muted">
        {t("console.activity_span", { from: formatDate(activity[0]?.day, lang), to: formatDate(activity.at(-1)?.day, lang) })}
      </figcaption>
    </figure>
  );
}

function UsersTab() {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const me = useMe().data;
  const [q, setQ] = useState("");
  const users = useAdminUsers(q.trim());
  const act = useUserAction();
  const toast = useToast();
  const run = (id: string, action: "role" | "unlock" | "sign-out", role?: Role) =>
    act.mutate({ id, action, role }, { onSuccess: () => toast(t(`console.done_${action.replace("-", "_")}`)) });
  return (
    <section>
      <label className="mb-4 block max-w-sm">
        <span className="sr-only">{t("console.search_users")}</span>
        <input type="search" value={q} onChange={(e) => setQ(e.target.value)} className={fieldClass} placeholder={t("console.search_users")} />
      </label>
      {act.isError && <div className="mb-3"><ErrorNote error={act.error} /></div>}
      {users.isPending && <Loading />}
      {users.isError && <ErrorNote error={users.error} />}
      {users.data && (
        <div className="overflow-x-auto rounded-lg border border-hairline bg-raised">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-hairline text-muted">
              <tr>
                {["email", "role", "security", "people", "last_sign_in", "actions"].map((c) => (
                  <th key={c} className="px-3 py-2 font-medium">{t(`console.u_${c}`)}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-hairline">
              {users.data.map((u) => (
                <tr key={u.id}>
                  <td className="px-3 py-2">
                    <span className="font-medium">{u.email}</span>
                    {u.id === me?.id && <span className="ml-1.5 text-xs text-muted">({t("console.you")})</span>}
                  </td>
                  <td className="px-3 py-2">
                    <select value={u.role} disabled={u.id === me?.id || act.isPending} aria-label={t("console.role_of", { email: u.email })}
                      onChange={(e) => run(u.id, "role", e.target.value as Role)} className={clsx(fieldClass, "w-auto py-1 text-sm")}>
                      {ROLES.map((r) => <option key={r} value={r}>{t(`console.role_${r}`)}</option>)}
                    </select>
                  </td>
                  <td className="px-3 py-2">
                    <span className="flex flex-wrap gap-1 text-xs">
                      <Badge ok={u.verified} label={t(u.verified ? "console.verified" : "console.unverified")} />
                      <Badge ok={u.totp} label={t(u.totp ? "console.two_step_on" : "console.two_step_off")} />
                      {u.locked && <Badge ok={false} label={t("console.locked")} />}
                    </span>
                  </td>
                  <td className="tabular px-3 py-2">{u.profiles}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-muted">{u.last_login_at ? formatDate(u.last_login_at, lang) : "—"}</td>
                  <td className="px-3 py-2">
                    <span className="flex flex-wrap gap-3">
                      {u.locked && (
                        <button type="button" className="text-link hover:underline" onClick={() => run(u.id, "unlock")}>{t("console.unlock")}</button>
                      )}
                      {u.sessions > 0 && u.id !== me?.id && (
                        <button type="button" className="text-link hover:underline" onClick={() => run(u.id, "sign-out")}>
                          {t("console.sign_out", { count: u.sessions })}
                        </button>
                      )}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="mt-3 max-w-prose text-sm text-muted">{t("console.users_note")}</p>
    </section>
  );
}

function Badge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className={clsx("inline-flex items-center gap-1 rounded-full border px-2 py-0.5",
      ok ? "border-normal/40 text-normal" : "border-borderline/50 text-borderline")}>
      <Icon name={ok ? "check" : "info"} size={12} />{label}
    </span>
  );
}

function JobsTab({ canRetry }: { canRetry: boolean }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const [state, setState] = useState("");
  const jobs = useJobs(state);
  const retry = useRetryJob();
  const toast = useToast();
  return (
    <section>
      <div role="group" aria-label={t("console.filter_state")} className="mb-4 flex flex-wrap gap-2">
        {["", "queued", "running", "failed", "succeeded"].map((s) => (
          <button key={s || "all"} type="button" aria-pressed={state === s} onClick={() => setState(s)}
            className={clsx("btn rounded-full border px-3 py-1 text-sm", state === s ? "border-ink/60 bg-sunken font-medium" : "border-hairline bg-raised hover:border-ink/40")}>
            {t(`console.job_${s || "all"}`)}
          </button>
        ))}
      </div>
      {retry.isError && <div className="mb-3"><ErrorNote error={retry.error} /></div>}
      {jobs.isPending && <Loading />}
      {jobs.data?.length === 0 && <Empty icon="clock">{t("console.no_jobs")}</Empty>}
      {jobs.data && jobs.data.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-hairline bg-raised">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-hairline text-muted">
              <tr>{["id", "stage", "status", "attempts", "when", "error", ""].map((c) => <th key={c} className="px-3 py-2 font-medium">{c && t(`console.j_${c}`)}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-hairline">
              {jobs.data.map((j) => (
                <tr key={j.id}>
                  <td className="tabular px-3 py-1.5 text-muted">{j.id}</td>
                  <td className="px-3 py-1.5">{t(`console.stage_${j.stage}`, j.stage)}</td>
                  <td className="px-3 py-1.5">
                    <span className={clsx("inline-flex items-center gap-1", j.status === "failed" ? "text-abnormal" : j.status === "succeeded" ? "text-normal" : "text-borderline")}>
                      <Icon name={j.status === "failed" ? "alert" : j.status === "succeeded" ? "check" : "clock"} size={14} />
                      {t(`console.job_${j.status}`, j.status)}
                    </span>
                  </td>
                  <td className="tabular px-3 py-1.5">{j.attempts}</td>
                  <td className="whitespace-nowrap px-3 py-1.5 text-muted">{formatDateTime(j.finished_at ?? j.created_at, lang)}</td>
                  <td className="max-w-xs truncate px-3 py-1.5 font-mono text-xs text-muted" title={j.error ?? ""}>{j.error}</td>
                  <td className="px-3 py-1.5">
                    {canRetry && j.status === "failed" && (
                      <Button className="px-2 py-0.5 text-sm" disabled={retry.isPending}
                        onClick={() => retry.mutate(j.id, { onSuccess: () => toast(t("console.retried")) })}>{t("console.retry")}</Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function AuditTab() {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const [action, setAction] = useState("");
  const [pages, setPages] = useState<number[]>([]);
  const before = pages.at(-1);
  const audit = useAudit(action.trim(), before);
  return (
    <section>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <label className="max-w-xs flex-1">
          <span className="sr-only">{t("console.filter_action")}</span>
          <input type="search" value={action} onChange={(e) => { setAction(e.target.value); setPages([]); }} className={fieldClass}
            placeholder={t("console.filter_action")} />
        </label>
        <p className="text-sm text-muted">{t("console.audit_note")}</p>
      </div>
      {audit.isPending && <Loading />}
      {audit.data?.length === 0 && <Empty icon="book">{t("console.no_audit")}</Empty>}
      {audit.data && audit.data.length > 0 && (
        <>
          <div className="overflow-x-auto rounded-lg border border-hairline bg-raised">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-hairline text-muted">
                <tr>{["when", "who", "action", "what", "details"].map((c) => <th key={c} className="px-3 py-2 font-medium">{t(`console.a_${c}`)}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-hairline">
                {audit.data.map((a) => <AuditRow key={a.id} a={a} lang={lang} />)}
              </tbody>
            </table>
          </div>
          <div className="mt-3 flex gap-3">
            {pages.length > 0 && <Button variant="quiet" className="px-0" onClick={() => setPages(pages.slice(0, -1))}>← {t("console.newer")}</Button>}
            {audit.data.length === 100 && (
              <Button variant="quiet" className="px-0" onClick={() => setPages([...pages, audit.data.at(-1)!.id])}>{t("console.older")} →</Button>
            )}
          </div>
        </>
      )}
    </section>
  );
}

function AuditRow({ a, lang }: { a: AuditEntry; lang: string }) {
  return (
    <tr>
      <td className="whitespace-nowrap px-3 py-1.5 text-muted">{formatDateTime(a.at, lang)}</td>
      <td className="px-3 py-1.5">{a.actor ?? "—"}</td>
      <td className="px-3 py-1.5 font-mono text-xs">{a.action}</td>
      <td className="whitespace-nowrap px-3 py-1.5 text-muted">{a.entity_type}{a.entity_id && <span className="font-mono text-xs"> {a.entity_id.slice(0, 8)}</span>}</td>
      <td className="px-3 py-1.5 font-mono text-xs text-muted">
        {a.meta && Object.entries(a.meta).map(([k, v]) => `${k}=${typeof v === "object" ? JSON.stringify(v) : String(v)}`).join(" ")}
      </td>
    </tr>
  );
}
