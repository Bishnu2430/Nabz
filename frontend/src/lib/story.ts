import type { BodyMapFrame, HealthRecord, ObsStatus, ReportSummary, ResultBrief } from "../api/types";
import { deviation } from "./format";

/**
 * A person's reports told as a story: one chapter per report or other record, each with its turning points.
 * Everything is a fact from the confirmed results (a value left its range, came back, reached its highest so
 * far); nothing is inferred about causes or conditions.
 */

export type StoryEvent =
  | { kind: "first"; total: number; outTotal: number; out: ResultBrief[] }
  | { kind: "critical"; result: ResultBrief }
  | { kind: "out"; result: ResultBrief; previous?: ResultBrief }
  | { kind: "back"; result: ResultBrief; previous: ResultBrief }
  | { kind: "peak"; result: ResultBrief; extreme: "highest" | "lowest" }
  | { kind: "worse"; result: ResultBrief; previous: ResultBrief }
  | { kind: "better"; result: ResultBrief; previous: ResultBrief }
  | { kind: "clear"; total: number }
  | { kind: "note"; text: string }
  | { kind: "record"; record: HealthRecord };

export interface Chapter {
  key: string;
  date: string;
  /** The report this chapter is about; a record chapter keeps the body as it was at the report before it. */
  frame?: BodyMapFrame;
  isRecord: boolean;
  events: StoryEvent[];
  /** Turning points left out to keep the chapter short. */
  more: number;
}

const ABNORMAL = new Set<ObsStatus>(["low", "high", "critical_low", "critical_high"]);
const isOut = (r: ResultBrief) => ABNORMAL.has(r.status);
const isCritical = (r: ResultBrief) => r.status.startsWith("critical");
const gap = (r: ResultBrief) => deviation(r)?.fraction ?? 0;
const MAX_EVENTS = 5;
/** The first report and critical values lead; then whatever is furthest from its range; good news is kept in view. */
function weight(e: StoryEvent): number {
  if (e.kind === "first") return 100;
  if (e.kind === "critical") return 50 + gap(e.result);
  if (e.kind === "back") return 0.2;
  if (e.kind === "clear") return 0.1;
  return "result" in e ? gap(e.result) : 0;
}

export function buildStory(frames: BodyMapFrame[], records: HealthRecord[], reports: ReportSummary[]): Chapter[] {
  const notes = new Map(reports.filter((r) => r.note).map((r) => [r.id, r.note as string]));
  const history = new Map<string, ResultBrief[]>();
  const chapters: Chapter[] = [];

  [...frames].sort((a, b) => a.date.localeCompare(b.date)).forEach((frame, index) => {
    const results = frame.organs.flatMap((o) => o.tests);
    const events: StoryEvent[] = [];
    if (index === 0) {
      const out = results.filter(isOut).sort((a, b) => gap(b) - gap(a));
      events.push({ kind: "first", total: results.length, outTotal: out.length, out: out.slice(0, 4) });
      results.filter(isCritical).forEach((result) => events.push({ kind: "critical", result }));
    } else {
      for (const result of results) {
        const past = history.get(result.test_code) ?? [];
        const previous = past[past.length - 1];
        if (isCritical(result)) events.push({ kind: "critical", result });
        else if (isOut(result) && (!previous || !isOut(previous))) events.push({ kind: "out", result, previous });
        else if (!isOut(result) && previous && isOut(previous)) events.push({ kind: "back", result, previous });
        else if (isOut(result) && previous && isOut(previous)) {
          const value = Number(result.value);
          const earlier = past.map((p) => Number(p.value));
          const high = result.status === "high";
          const extreme = high ? value > Math.max(...earlier) : value < Math.min(...earlier);
          if (extreme && past.length >= 2) events.push({ kind: "peak", result, extreme: high ? "highest" : "lowest" });
          else if (gap(result) > gap(previous) * 1.05 + 0.01) events.push({ kind: "worse", result, previous });
          else if (gap(result) < gap(previous) * 0.95 - 0.01) events.push({ kind: "better", result, previous });
        }
      }
      if (!results.some(isOut)) events.push({ kind: "clear", total: results.length });
    }
    for (const r of results) history.set(r.test_code, [...(history.get(r.test_code) ?? []), r]);

    events.sort((a, b) => weight(b) - weight(a));
    const shown = events.slice(0, MAX_EVENTS);
    const note = notes.get(frame.report_id);
    if (note) shown.push({ kind: "note", text: note });
    chapters.push({ key: frame.report_id, date: frame.date, frame, isRecord: false, events: shown,
      more: Math.max(0, events.length - MAX_EVENTS) });
  });

  for (const record of records) {
    if (!record.record_date) continue;
    chapters.push({ key: record.id, date: record.record_date, isRecord: true, events: [{ kind: "record", record }], more: 0 });
  }
  // a record on the same day as a report comes after it
  chapters.sort((a, b) => a.date.localeCompare(b.date) || Number(a.isRecord) - Number(b.isRecord));

  // a record chapter shows the body as the report before it left it
  let last: BodyMapFrame | undefined;
  for (const c of chapters) {
    if (c.frame) last = c.frame;
    else c.frame = last;
  }
  return chapters;
}

/** How long a chapter stays on screen when it isn't being read aloud. */
export function chapterMs(chapter: Chapter): number {
  return Math.min(3200 + chapter.events.length * 1700, 11000);
}
