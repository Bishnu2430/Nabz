import clsx from "clsx";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { recordImageUrl, useBodyMap, useProfiles, useRecords, useReports } from "../api/hooks";
import type { ResultBrief } from "../api/types";
import { BodyStage } from "../components/body/BodyMap";
import { isOrganCode, type OrganCode, type OrganStatus } from "../components/body/organs";
import { useExact, ValueChips } from "../components/exact/exact";
import { StatusIcon } from "../components/insights/StatusMark";
import { IconSeal } from "../components/icons";
import { Button, ErrorNote, Loading } from "../components/ui";
import { formatDate, formatRange, formatWithUnit } from "../lib/format";
import { buildStory, chapterMs, type Chapter, type StoryEvent } from "../lib/story";

const SPEEDS = [1, 1.5, 2] as const;
const VOICE: Record<string, string> = { en: "en-IN", hi: "hi-IN", or: "or-IN" };

/**
 * Story mode: a person's reports replayed in order. The body takes each report's colours while the turning points
 * are listed beside it: what left its range, what came back, what reached its highest so far. It can be read
 * aloud by the browser. Only facts from the confirmed results are stated.
 */
export default function Story() {
  const { id = "" } = useParams();
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const profile = useProfiles().data?.find((p) => p.id === id);
  const frames = useBodyMap(id);
  const records = useRecords(id);
  const reports = useReports(id);
  const chapters = useMemo(
    () => buildStory(frames.data ?? [], records.data ?? [], reports.data ?? []),
    [frames.data, records.data, reports.data],
  );
  const caption = useCaptions();

  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<(typeof SPEEDS)[number]>(1);
  const [aloud, setAloud] = useState(false);
  const canSpeak = typeof window !== "undefined" && "speechSynthesis" in window;
  const chapter: Chapter | undefined = chapters[index];
  const last = index >= chapters.length - 1;
  const advance = useRef<() => void>(() => {});
  advance.current = () => {
    if (last) setPlaying(false);
    else setIndex((i) => i + 1);
  };

  // move on when the chapter has been shown long enough, or when it has been read out
  useEffect(() => {
    if (!playing || !chapter) return;
    if (aloud && canSpeak) {
      const say = new SpeechSynthesisUtterance(
        [formatDate(chapter.date, lang), ...chapter.events.map((e) => caption(e).text)].join(". "));
      say.lang = VOICE[lang] ?? "en-IN";
      say.rate = speed === 1 ? 1 : speed === 1.5 ? 1.2 : 1.4;
      let done = false;
      const next = () => {
        if (!done) {
          done = true;
          window.setTimeout(() => advance.current(), 500);
        }
      };
      say.onend = next;
      say.onerror = next;
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(say);
      return () => {
        done = true;
        window.speechSynthesis.cancel();
      };
    }
    const timer = window.setTimeout(() => advance.current(), chapterMs(chapter) / speed);
    return () => window.clearTimeout(timer);
    // `caption` only depends on the language, which is listed
  }, [playing, index, speed, aloud, chapter, lang]);

  const go = useCallback((to: number) => {
    setIndex(Math.min(Math.max(to, 0), Math.max(chapters.length - 1, 0)));
  }, [chapters.length]);

  // space plays and pauses; the arrow keys step
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).closest("input, select, textarea, button, a")) return;
      if (e.key === " ") setPlaying((p) => !p);
      else if (e.key === "ArrowRight") go(index + 1);
      else if (e.key === "ArrowLeft") go(index - 1);
      else return;
      e.preventDefault();
    };
    document.addEventListener("keydown", key);
    return () => document.removeEventListener("keydown", key);
  }, [go, index]);

  if (frames.isPending || records.isPending || reports.isPending) return <Loading />;
  if (frames.isError) return <ErrorNote error={frames.error} />;
  if (!chapter) {
    return (
      <>
        <Link to={`/p/${id}`} className="text-link">← {profile?.display_name}</Link>
        <p className="mt-6 text-muted">{t("story.empty")}</p>
      </>
    );
  }

  const statuses: OrganStatus = {};
  for (const o of chapter.frame?.organs ?? []) if (isOrganCode(o.code)) statuses[o.code as OrganCode] = o.status;
  const names = Object.fromEntries((chapter.frame?.organs ?? []).map((o) => [o.code, t(`organs.${o.code}`)]));
  const record = chapter.events.find((e) => e.kind === "record");
  const play = () => {
    if (last) setIndex(0);
    setPlaying(true);
  };

  return (
    <>
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <Link to={`/p/${id}`} className="text-link">← {profile?.display_name}</Link>
        <p className="text-sm text-muted">{t("story.keys")}</p>
      </div>
      <div className="page-head mb-5 mt-2 flex items-center gap-4">
        <IconSeal name="play" size={24} className="icon-seal-lg" />
        <h1 className="font-display text-3xl font-bold sm:text-4xl">{t("story.title", { name: profile?.display_name ?? "" })}</h1>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
        <div className="relative">
          {record?.kind === "record" && record.record.has_image ? (
            <div key={chapter.key} className="fade-in grid h-[420px] place-items-center overflow-hidden rounded-lg border border-hairline bg-black sm:h-[520px]">
              <img src={recordImageUrl(record.record.id)} alt="" className="max-h-full max-w-full object-contain" />
            </div>
          ) : (
            <BodyStage statuses={statuses} names={names} className="h-[420px] sm:h-[520px]" />
          )}
          <p className="pointer-events-none absolute left-4 top-3 font-display text-5xl font-bold text-white/85 drop-shadow"
            aria-hidden="true">
            {chapter.date.slice(0, 4)}
          </p>
        </div>

        <section aria-live={playing && aloud ? "off" : "polite"} aria-labelledby="chapter-h" className="flex flex-col">
          <div key={chapter.key} className="rise flex-1">
            <p className="text-sm text-muted">
              {t("story.chapter", { n: index + 1, total: chapters.length })}
              {chapter.frame?.lab_name && !chapter.isRecord && ` · ${chapter.frame.lab_name}`}
            </p>
            <h2 id="chapter-h" className="font-display text-3xl font-bold">{formatDate(chapter.date, lang)}</h2>
            <ul className="stagger mt-4 space-y-3">
              {chapter.events.map((e, i) => <li key={i}><EventLine event={e} caption={caption(e)} profileId={id} /></li>)}
            </ul>
            {chapter.more > 0 && <p className="mt-3 text-sm text-muted">{t("story.more", { count: chapter.more })}</p>}
            {chapter.frame && !chapter.isRecord && (
              <Link to={`/r/${chapter.frame.report_id}`} className="mt-4 inline-block text-link">
                {t("body.open_report_on", { date: formatDate(chapter.date, lang) })} →
              </Link>
            )}
          </div>

          <div className="mt-6">
            {/* how far through this chapter the story is */}
            <div className="h-1 overflow-hidden rounded-full bg-sunken" aria-hidden="true">
              <div key={`${chapter.key}-${playing}-${speed}`} className={clsx("h-full bg-accent", playing && !aloud && "story-progress")}
                style={{ animationDuration: `${chapterMs(chapter) / speed}ms`, width: playing && !aloud ? undefined : "0%" }} />
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <Button variant="primary" onClick={playing ? () => setPlaying(false) : play} aria-pressed={playing}>
                {playing ? t("body.pause") : last ? t("story.replay") : t("body.play")}
              </Button>
              <Button onClick={() => go(index - 1)} disabled={index === 0} aria-label={t("story.previous")}>←</Button>
              <Button onClick={() => go(index + 1)} disabled={last} aria-label={t("story.next")}>→</Button>
              <label className="ml-2 flex items-center gap-2 text-sm">
                <span className="text-muted">{t("story.speed")}</span>
                <select value={speed} onChange={(e) => setSpeed(Number(e.target.value) as (typeof SPEEDS)[number])}
                  className="rounded-md border border-hairline bg-raised px-2 py-1">
                  {SPEEDS.map((s) => <option key={s} value={s}>{s}×</option>)}
                </select>
              </label>
              {canSpeak && (
                <label className="flex cursor-pointer items-center gap-2 text-sm">
                  <input type="checkbox" checked={aloud} onChange={(e) => setAloud(e.target.checked)}
                    className="size-4 accent-[var(--accent)]" />
                  {t("story.read_aloud")}
                </label>
              )}
            </div>
          </div>
        </section>
      </div>

      {/* the whole story as a strip of dates */}
      <ol aria-label={t("story.chapters")} className="mt-6 flex gap-1.5 overflow-x-auto pb-2 [scrollbar-width:thin]">
        {chapters.map((c, i) => (
          <li key={c.key}>
            <button type="button" onClick={() => { setPlaying(false); go(i); }} aria-current={i === index ? "step" : undefined}
              className={clsx("whitespace-nowrap rounded-full border px-3 py-1 text-sm transition",
                i === index ? "border-ink bg-raised font-medium" : i < index ? "border-hairline text-ink" : "border-hairline text-muted",
                "hover:border-ink/40")}>
              {c.isRecord ? "◇ " : ""}{formatDate(c.date, lang)}
            </button>
          </li>
        ))}
      </ol>
      <p className="mt-4 max-w-prose text-sm text-muted">{t("story.note")}</p>
    </>
  );
}

interface Caption {
  text: string;
  tone: "out" | "back" | "critical" | "plain";
  chips?: ResultBrief[];
  result?: ResultBrief;
}

/** Each turning point as a sentence, in the reader's language, with the exact values. */
function useCaptions() {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const { describe } = useExact();
  return (e: StoryEvent): Caption => {
    const v = (r: ResultBrief) => formatWithUnit(r);
    const base = (r: ResultBrief) => ({ test: r.test_name, value: v(r), range: formatRange(r.ref_low, r.ref_high) || "—",
      how: describe(r) });
    switch (e.kind) {
      case "first":
        return { tone: e.out.length ? "out" : "plain", chips: e.out,
          text: e.outTotal ? t("story.first_out", { total: e.total, count: e.outTotal }) : t("story.first_clear", { total: e.total }) };
      case "critical":
        return { tone: "critical", result: e.result, text: t("story.critical", base(e.result)) };
      case "out":
        return { tone: "out", result: e.result, text: e.previous
          ? t("story.out_from", { ...base(e.result), previous: v(e.previous), date: formatDate(e.previous.date, lang) })
          : t("story.out", base(e.result)) };
      case "back":
        return { tone: "back", result: e.result, text: t("story.back", { ...base(e.result), previous: v(e.previous) }) };
      case "peak":
        return { tone: "out", result: e.result, text: t(`story.${e.extreme}`, base(e.result)) };
      case "worse":
        return { tone: "out", result: e.result, text: t("story.worse", { ...base(e.result), previous: v(e.previous) }) };
      case "better":
        return { tone: "back", result: e.result, text: t("story.better", { ...base(e.result), previous: v(e.previous) }) };
      case "clear":
        return { tone: "back", text: t("story.clear", { total: e.total }) };
      case "note":
        return { tone: "plain", text: t("story.noted", { note: e.text }) };
      case "record":
        return { tone: "plain", text: [e.record.title, e.record.facility, e.record.impression?.[0]].filter(Boolean).join(". ") };
    }
  };
}

function EventLine({ event, caption, profileId }: { event: StoryEvent; caption: Caption; profileId: string }) {
  const { t } = useTranslation();
  const tone = { out: "border-abnormal/40", back: "border-normal/50", critical: "border-critical bg-critical/5",
    plain: "border-hairline" }[caption.tone];
  return (
    <div className={clsx("rounded-lg border bg-raised px-4 py-3", tone)}>
      <p className="flex gap-2.5">
        {caption.result && (
          <span className={clsx("mt-1 shrink-0", caption.tone === "back" ? "text-normal" : "text-abnormal")}>
            <StatusIcon status={caption.result.status} />
          </span>
        )}
        <span className={event.kind === "note" ? "italic" : undefined}>{caption.text}</span>
      </p>
      {caption.chips && caption.chips.length > 0 && (
        <div className="mt-2">
          <ValueChips values={caption.chips} max={4} linkTo={(v) => `/p/${profileId}/tests/${v.test_code}`} />
        </div>
      )}
      {caption.result && (
        <Link to={`/p/${profileId}/tests/${caption.result.test_code}`} className="mt-1 inline-block text-sm text-link">
          {t("organ.full_history")} →
        </Link>
      )}
    </div>
  );
}
