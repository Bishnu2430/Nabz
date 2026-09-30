import type { BodyMapFrame, ResultBrief } from "../api/types";

export interface TestSeries {
  code: string;
  organ: string;
  latest: ResultBrief;
  results: ResultBrief[]; // oldest first
}

/** Every test a person has had, with all its results, from the body-map frames (one per confirmed report). */
export function seriesByTest(frames: BodyMapFrame[]): TestSeries[] {
  const map = new Map<string, TestSeries>();
  for (const frame of frames) {
    for (const organ of frame.organs) {
      for (const r of organ.tests) {
        const s = map.get(r.test_code) ?? { code: r.test_code, organ: organ.code, latest: r, results: [] };
        s.results.push(r);
        map.set(r.test_code, s);
      }
    }
  }
  for (const s of map.values()) {
    s.results.sort((a, b) => a.date.localeCompare(b.date));
    s.latest = s.results[s.results.length - 1];
  }
  return [...map.values()];
}

/** The results of one report, keyed by test. */
export function frameResults(frame: BodyMapFrame | undefined): Map<string, ResultBrief> {
  const map = new Map<string, ResultBrief>();
  for (const organ of frame?.organs ?? []) for (const r of organ.tests) map.set(r.test_code, r);
  return map;
}
