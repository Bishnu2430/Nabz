/**
 * The explanation's summary arrives as text: an opening line, one "• …" line per out-of-range result, and a
 * closing line. These helpers take it apart so each result can be shown as a card with its numbers drawn, while
 * every word shown is still the checked text.
 */

export interface SummaryParts {
  intro: string[];
  bullets: string[];
  closing: string[];
}

export function parseSummary(summary: string): SummaryParts {
  const lines = summary.split("\n").map((l) => l.trim()).filter(Boolean);
  const isBullet = (l: string) => /^[•\-*]\s+/.test(l);
  const first = lines.findIndex(isBullet);
  if (first < 0) return { intro: lines, bullets: [], closing: [] };
  let last = first;
  lines.forEach((l, i) => {
    if (isBullet(l)) last = i;
  });
  return {
    intro: lines.slice(0, first),
    bullets: lines.slice(first, last + 1).filter(isBullet).map((l) => l.replace(/^[•\-*]\s+/, "")),
    closing: lines.slice(last + 1),
  };
}

/**
 * A bullet's first sentence restates the value and range (drawn on the card instead); the rest says what the
 * result can go along with. Sentences end with "." or the danda "।"; a "." inside a number is not an end.
 */
export function bulletRest(bullet: string): string {
  const end = bullet.search(/[.।](?=\s+\S)/);
  return end < 0 ? "" : bullet.slice(end + 1).trim();
}

/** The result a bullet is about: the one whose name the bullet starts with (the longest such name). */
export function matchBullet<T extends { test_name: string }>(bullet: string, results: T[]): T | undefined {
  const text = bullet.toLowerCase();
  let best: T | undefined;
  for (const r of results) {
    if (text.startsWith(r.test_name.toLowerCase()) && (!best || r.test_name.length > best.test_name.length)) best = r;
  }
  return best;
}
