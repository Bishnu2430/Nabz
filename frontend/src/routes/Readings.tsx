import clsx from "clsx";
import { useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams, useSearchParams } from "react-router-dom";

import {
  READING_KINDS, READING_UNIT, useAddReading, useDeleteReading, useReadingTargets, useReadings, useSetReadingTarget,
  type Reading, type ReadingKind, type ReadingTarget,
} from "../api/care";
import { useProfiles } from "../api/hooks";
import { ReadingChart } from "../components/care/ReadingChart";
import { useToast } from "../components/Toast";
import { Button, Card, ErrorNote, Loading, PageTitle, fieldClass } from "../components/ui";
import { formatDate, formatDateTime } from "../lib/format";
import { formatReadingNumber, misses, readingStats, readingText, targetText, within, type Miss } from "../lib/readings";
import NotFound from "./NotFound";

const CONTEXTS: Record<ReadingKind, string[]> = {
  bp: ["morning", "evening"],
  glucose: ["fasting", "before_meal", "after_meal", "bedtime"],
  pulse: ["resting", "after_activity"],
  weight: [], temperature: [], spo2: [],
};
const PERIODS = [30, 90, 365, null] as const;
const STEP: Record<ReadingKind, string> = { bp: "1", glucose: "1", weight: "0.1", pulse: "1", temperature: "0.1", spo2: "1" };

/** How a reading sits against the person's own target, in exact numbers. */
function useAgainst(kind: ReadingKind) {
  const { t } = useTranslation();
  const one = (m: Miss) => {
    const text = t(`readings.${m.side}`, { by: formatReadingNumber(m.by, kind), bound: formatReadingNumber(m.bound, kind) });
    return kind === "bp" ? `${t(m.which === "value" ? "readings.upper" : "readings.lower")} ${text}` : text;
  };
  return (r: Reading, target: ReadingTarget | undefined): { text: string; outside: boolean } => {
    const range = targetText(kind, target);
    if (!range) return { text: t("readings.no_target"), outside: false };
    const m = misses(r, target);
    return m.length ? { text: m.map(one).join("; "), outside: true } : { text: t("readings.in_target", { target: range }), outside: false };
  };
}

/**
 * Readings a person takes at home (blood pressure, blood sugar, weight and so on), kept beside the lab reports.
 * Nabz compares them only with the target the person enters from their own doctor; it has no opinion of its own.
 */
export default function Readings() {
  const { id = "" } = useParams();
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const [params, setParams] = useSearchParams();
  const profiles = useProfiles();
  const readings = useReadings(id);
  const targets = useReadingTargets(id);
  const [days, setDays] = useState<(typeof PERIODS)[number]>(90);

  const byKind = useMemo(() => {
    const map = new Map<ReadingKind, Reading[]>();
    for (const r of readings.data ?? []) map.set(r.kind, [...(map.get(r.kind) ?? []), r]);
    return map;
  }, [readings.data]);
  const asked = params.get("kind") as ReadingKind | null;
  const kind: ReadingKind = asked && READING_KINDS.includes(asked) ? asked
    : READING_KINDS.find((k) => byKind.has(k)) ?? "bp";
  const against = useAgainst(kind);

  if (profiles.isPending || readings.isPending) return <Loading />;
  if (profiles.isError) return <ErrorNote error={profiles.error} />;
  const profile = profiles.data.find((p) => p.id === id);
  if (!profile) return <NotFound />;
  if (readings.isError) return <ErrorNote error={readings.error} onRetry={() => void readings.refetch()} />;

  const all = byKind.get(kind) ?? [];
  const target = targets.data?.[kind];
  const shown = within(all, days);
  const stats = readingStats(shown, target);
  const latest = all[0];
  const unit = READING_UNIT[kind];
  const range = targetText(kind, target);

  return (
    <>
      <Link to={`/p/${id}`} className="text-link">← {profile.display_name}</Link>
      <PageTitle title={t("readings.title")} subtitle={t("readings.intro")} />

      <div role="tablist" aria-label={t("readings.kinds")} className="-mt-3 mb-6 flex flex-wrap gap-2">
        {READING_KINDS.map((k) => (
          <button key={k} type="button" role="tab" aria-selected={k === kind} onClick={() => setParams({ kind: k }, { replace: true })}
            className={clsx("btn rounded-full border px-3 py-1 text-sm", k === kind
              ? "border-accent bg-accent font-medium text-accent-ink" : "border-hairline bg-raised hover:border-ink/40")}>
            {t(`readings.kind_${k}`)}{" "}
            {byKind.has(k) && <span className="tabular opacity-70">{byKind.get(k)!.length}</span>}
          </button>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="min-w-0 space-y-6">
          {latest ? (
            <>
              <div className="flex flex-wrap items-end gap-x-8 gap-y-2">
                <div>
                  <p className="text-sm text-muted">{t("readings.latest")} · {formatDateTime(latest.taken_at, lang)}</p>
                  <p className="text-4xl font-semibold tabular">
                    {readingText(latest)} <span className="text-lg font-normal text-muted">{unit}</span>
                  </p>
                </div>
                <p className={clsx("pb-1", against(latest, target).outside ? "font-medium text-abnormal" : "text-muted")}>
                  {against(latest, target).text}
                </p>
              </div>

              <Card className="p-4">
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <div role="group" aria-label={t("readings.period")} className="flex flex-wrap gap-1.5 text-sm">
                    {PERIODS.map((p) => (
                      <button key={p ?? "all"} type="button" aria-pressed={p === days} onClick={() => setDays(p)}
                        className={clsx("rounded-full border px-2.5 py-0.5", p === days
                          ? "border-ink/60 bg-sunken font-medium" : "border-hairline hover:border-ink/40")}>
                        {p ? t("readings.last_days", { count: p }) : t("readings.all_time")}
                      </button>
                    ))}
                  </div>
                  {range && <p className="text-sm text-normal">{t("readings.target_is", { target: range, unit })}</p>}
                </div>
                {shown.length > 0 ? <ReadingChart kind={kind} readings={shown} target={target} />
                  : <p className="py-10 text-center text-muted">{t("readings.none_in_period")}</p>}
              </Card>

              {stats && (
                <Card className="space-y-1.5 p-5">
                  <p>
                    <span className="font-medium">{t("readings.average", { count: stats.count })}</span>{" "}
                    <span className="tabular font-semibold">
                      {formatReadingNumber(stats.mean, kind)}{stats.mean2 != null && `/${formatReadingNumber(stats.mean2, kind)}`} {unit}
                    </span>
                  </p>
                  <p className="text-muted">
                    {t("readings.lowest", { value: `${readingText(stats.lowest)} ${unit}`, date: formatDate(stats.lowest.taken_at, lang) })}
                    {" · "}
                    {t("readings.highest", { value: `${readingText(stats.highest)} ${unit}`, date: formatDate(stats.highest.taken_at, lang) })}
                  </p>
                  {stats.outside != null && (
                    <p className={stats.outside ? "text-abnormal" : "text-normal"}>
                      {stats.outside && stats.furthest
                        ? t("readings.outside", { count: stats.count, n: stats.outside, target: range, unit,
                          value: `${readingText(stats.furthest)} ${unit}`, date: formatDate(stats.furthest.taken_at, lang) })
                        : t("readings.all_inside", { count: stats.count, target: range, unit })}
                    </p>
                  )}
                </Card>
              )}
            </>
          ) : (
            <Card className="p-8 text-center">
              <h2 className="font-display text-xl font-bold">{t("readings.empty_title", { kind: t(`readings.kind_${kind}`) })}</h2>
              <p className="mt-1 text-muted">{t("readings.empty_body")}</p>
            </Card>
          )}
        </div>

        <div className="space-y-6">
          <AddReading key={kind} profileId={id} kind={kind} />
          <TargetEditor key={`${kind}-${JSON.stringify(target ?? {})}`} profileId={id} kind={kind} target={target} />
        </div>
      </div>

      {all.length > 0 && <ReadingTable key={kind} profileId={id} kind={kind} readings={all} target={target} />}
      <p className="mt-8 max-w-prose text-sm text-muted">{t("readings.note")}</p>
    </>
  );
}

function localNow(): string {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
}

function AddReading({ profileId, kind }: { profileId: string; kind: ReadingKind }) {
  const { t } = useTranslation();
  const add = useAddReading(profileId);
  const toast = useToast();
  const [value, setValue] = useState("");
  const [value2, setValue2] = useState("");
  const [when, setWhen] = useState("");
  const [context, setContext] = useState("");
  const [note, setNote] = useState("");
  const ready = value !== "" && (kind !== "bp" || value2 !== "");

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!ready) return;
    add.mutate({ kind, value: Number(value), value2: kind === "bp" ? Number(value2) : undefined,
      taken_at: when ? new Date(when).toISOString() : undefined, context: context || undefined, note: note.trim() || undefined }, {
      onSuccess: () => {
        toast(t("readings.saved"));
        setValue("");
        setValue2("");
        setNote("");
        setWhen("");
      },
    });
  };

  return (
    <Card className="p-5">
      <h2 className="mb-3 font-display text-lg font-bold">{t("readings.add")}</h2>
      <form onSubmit={submit} className="space-y-3" noValidate>
        <div className="flex items-end gap-2">
          <label className="min-w-0 flex-1">
            <span className="mb-1 block font-medium">{kind === "bp" ? t("readings.upper_label") : t(`readings.kind_${kind}`)}</span>
            <input type="number" inputMode="decimal" step={STEP[kind]} value={value} onChange={(e) => setValue(e.target.value)}
              className={clsx(fieldClass, "tabular")} />
          </label>
          {kind === "bp" && (
            <>
              <span className="pb-2 text-xl text-muted" aria-hidden="true">/</span>
              <label className="min-w-0 flex-1">
                <span className="mb-1 block font-medium">{t("readings.lower_label")}</span>
                <input type="number" inputMode="decimal" step="1" value={value2} onChange={(e) => setValue2(e.target.value)}
                  className={clsx(fieldClass, "tabular")} />
              </label>
            </>
          )}
          <span className="pb-2 text-muted">{READING_UNIT[kind]}</span>
        </div>
        <label className="block">
          <span className="mb-1 block font-medium">{t("readings.when")}</span>
          <input type="datetime-local" value={when} max={localNow()} onChange={(e) => setWhen(e.target.value)} className={fieldClass} />
          <span className="mt-1 block text-sm text-muted">{t("readings.when_hint")}</span>
        </label>
        {CONTEXTS[kind].length > 0 && (
          <label className="block">
            <span className="mb-1 block font-medium">{t("readings.context")}</span>
            <select value={context} onChange={(e) => setContext(e.target.value)} className={fieldClass}>
              <option value="">{t("readings.context_none")}</option>
              {CONTEXTS[kind].map((c) => <option key={c} value={c}>{t(`readings.context_${c}`)}</option>)}
            </select>
          </label>
        )}
        <label className="block">
          <span className="mb-1 block font-medium">{t("records.notes")}</span>
          <input value={note} maxLength={200} onChange={(e) => setNote(e.target.value)} className={fieldClass}
            placeholder={t("readings.note_placeholder")} />
        </label>
        {add.isError && <ErrorNote error={add.error} />}
        <Button type="submit" variant="primary" disabled={!ready || add.isPending}>{t("readings.save")}</Button>
      </form>
    </Card>
  );
}

function TargetEditor({ profileId, kind, target }: { profileId: string; kind: ReadingKind; target?: ReadingTarget }) {
  const { t } = useTranslation();
  const save = useSetReadingTarget(profileId);
  const toast = useToast();
  const bp = kind === "bp";
  const start = (v?: string | null) => (v == null ? "" : formatReadingNumber(Number(v), kind));
  const [a, setA] = useState(start(bp ? target?.high : target?.low));
  const [b, setB] = useState(start(bp ? target?.high2 : target?.high));
  const has = Boolean(targetText(kind, target));

  const put = (body: Record<string, number>) =>
    save.mutate({ kind, target: body }, { onSuccess: () => toast(t(Object.keys(body).length ? "readings.target_saved" : "readings.target_removed")) });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    const body: Record<string, number> = {};
    if (a !== "") body[bp ? "high" : "low"] = Number(a);
    if (b !== "") body[bp ? "high2" : "high"] = Number(b);
    put(body);
  };

  return (
    <Card className="p-5">
      <h2 className="font-display text-lg font-bold">{t("readings.target_title")}</h2>
      <p className="mb-3 mt-1 text-sm text-muted">{t("readings.target_intro")}</p>
      <form onSubmit={submit} className="space-y-3" noValidate>
        <div className="flex items-end gap-2">
          <label className="min-w-0 flex-1">
            <span className="mb-1 block text-sm font-medium">{t(bp ? "readings.target_upper" : "readings.target_from")}</span>
            <input type="number" inputMode="decimal" step={STEP[kind]} value={a} onChange={(e) => setA(e.target.value)}
              className={clsx(fieldClass, "tabular")} />
          </label>
          <label className="min-w-0 flex-1">
            <span className="mb-1 block text-sm font-medium">{t(bp ? "readings.target_lower" : "readings.target_to")}</span>
            <input type="number" inputMode="decimal" step={STEP[kind]} value={b} onChange={(e) => setB(e.target.value)}
              className={clsx(fieldClass, "tabular")} />
          </label>
          <span className="pb-2 text-muted">{READING_UNIT[kind]}</span>
        </div>
        {save.isError && <ErrorNote error={save.error} />}
        <div className="flex flex-wrap gap-3">
          <Button type="submit" disabled={save.isPending || (a === "" && b === "")}>{t("readings.target_save")}</Button>
          {has && <Button variant="quiet" disabled={save.isPending} onClick={() => put({})}>{t("readings.target_remove")}</Button>}
        </div>
      </form>
    </Card>
  );
}

function ReadingTable({ profileId, kind, readings, target }: {
  profileId: string; kind: ReadingKind; readings: Reading[]; target?: ReadingTarget;
}) {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const remove = useDeleteReading(profileId);
  const against = useAgainst(kind);
  const [limit, setLimit] = useState(15);
  return (
    <section className="mt-8" aria-labelledby="readings-table-h">
      <h2 id="readings-table-h" className="mb-3 font-display text-xl font-bold">
        {t("readings.table_title", { kind: t(`readings.kind_${kind}`) })}
      </h2>
      <div className="overflow-x-auto rounded-lg border border-hairline bg-raised">
        <table className="w-full text-left">
          <thead className="border-b border-hairline text-sm text-muted">
            <tr>
              <th className="px-4 py-2 font-medium">{t("readings.when")}</th>
              <th className="px-4 py-2 font-medium">{t("readings.reading")}</th>
              <th className="px-4 py-2 font-medium">{t("readings.against")}</th>
              <th className="px-4 py-2 font-medium">{t("readings.context")}</th>
              <th className="px-4 py-2 font-medium">{t("records.notes")}</th>
              <th className="px-4 py-2"><span className="sr-only">{t("records.delete")}</span></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-hairline">
            {readings.slice(0, limit).map((r) => {
              const a = against(r, target);
              return (
                <tr key={r.id}>
                  <td className="whitespace-nowrap px-4 py-2">{formatDateTime(r.taken_at, lang)}</td>
                  <td className={clsx("tabular whitespace-nowrap px-4 py-2 font-medium", a.outside && "text-abnormal")}>
                    {readingText(r)} <span className="font-normal text-muted">{READING_UNIT[kind]}</span>
                  </td>
                  <td className={clsx("px-4 py-2 text-sm", a.outside ? "text-abnormal" : "text-muted")}>{a.text}</td>
                  <td className="px-4 py-2 text-sm">{r.context ? t(`readings.context_${r.context}`, r.context) : ""}</td>
                  <td className="px-4 py-2 text-sm text-muted">{r.note}</td>
                  <td className="px-4 py-2 text-right">
                    <button type="button" className="text-sm text-muted hover:text-abnormal hover:underline" disabled={remove.isPending}
                      aria-label={t("readings.delete_label", { value: readingText(r), date: formatDateTime(r.taken_at, lang) })}
                      onClick={() => remove.mutate(r.id)}>
                      {t("records.delete")}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {readings.length > limit && (
        <Button variant="quiet" className="mt-2 px-0" onClick={() => setLimit(limit + 30)}>
          {t("readings.show_more", { count: readings.length - limit })}
        </Button>
      )}
    </section>
  );
}
