/** Formatting helpers. Decimals arrive from the API as strings. */

/** "4.8030" -> "4.803", "140.00" -> "140". Keeps the string form so no float rounding creeps in. */
export function trimDecimal(value: string | null | undefined): string {
  if (value == null) return "";
  if (!value.includes(".")) return value;
  return value.replace(/0+$/, "").replace(/\.$/, "");
}

/**
 * A converted value to a readable precision: four significant figures, whole numbers from 1000 up.
 * 79.2704 -> "79.27", 1.821232 -> "1.821", 154.2933 -> "154.3", 150000 -> "150000".
 * Only for values Nabz computed; printed values keep the lab's own precision.
 */
export function formatComputed(value: string): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return value;
  if (Math.abs(n) >= 1000) return String(Math.round(n));
  return String(Number(n.toPrecision(4)));
}

const SUPERSCRIPT = "⁰¹²³⁴⁵⁶⁷⁸⁹";

/** Catalogue units are stored ASCII-friendly ("10^6/µL"); show them as printed on a report ("×10⁶/µL"). */
export function formatUnit(unit: string | null | undefined): string {
  if (!unit) return "";
  return unit.replace(/(?:x|×)?10\^(\d+)/g, (_, exp: string) => `×10${[...exp].map((d) => SUPERSCRIPT[Number(d)]).join("")}`);
}

export function formatRange(low: string | null, high: string | null): string {
  const lo = low == null ? "" : formatComputed(low);
  const hi = high == null ? "" : formatComputed(high);
  if (lo && hi) return `${lo} – ${hi}`;
  if (hi) return `< ${hi}`;
  if (lo) return `> ${lo}`;
  return "";
}

export function formatDate(iso: string | null | undefined, lang: string): string {
  if (!iso) return "";
  // Date-only strings are calendar dates: format them in UTC so they never shift a day.
  const d = new Date(iso.length === 10 ? `${iso}T00:00:00Z` : iso);
  return new Intl.DateTimeFormat(lang === "en" ? "en-IN" : `${lang}-IN`, {
    day: "numeric",
    month: "short",
    year: "numeric",
    ...(iso.length === 10 ? { timeZone: "UTC" } : {}),
  }).format(d);
}

/** Where a value sits against its range: used for the small status word beside each value. */
export type Position = "low" | "normal" | "high" | "unknown";

export function position(value: string | null, low: string | null, high: string | null): Position {
  if (value == null) return "unknown";
  const v = Number(value);
  if (low != null && v < Number(low)) return "low";
  if (high != null && v > Number(high)) return "high";
  if (low == null && high == null) return "unknown";
  return "normal";
}

/** A value at the test's display precision (catalogue `decimals`): "1.10", "14.0", "194". */
export function formatValue(value: string | number, decimals: number): string {
  const n = Number(value);
  return Number.isFinite(n) ? n.toFixed(decimals) : String(value);
}

/** A change as a signed percentage: +12 %, −4.5 %. */
export function formatPercent(fraction: number): string {
  const pct = fraction * 100;
  const digits = Math.abs(pct) >= 10 ? 0 : 1;
  const sign = pct > 0 ? "+" : pct < 0 ? "−" : "";
  return `${sign}${Math.abs(pct).toFixed(digits)} %`;
}

export function formatMonth(iso: string, lang: string): string {
  const d = new Date(`${iso.slice(0, 10)}T00:00:00Z`);
  return new Intl.DateTimeFormat(lang === "en" ? "en-IN" : `${lang}-IN`, { month: "short", year: "numeric", timeZone: "UTC" })
    .format(d);
}

/** Whole years or months between two ISO dates, for "over 3 years". */
export function spanYears(first: string, last: string): number {
  return (Date.parse(last) - Date.parse(first)) / (365.25 * 24 * 3600 * 1000);
}

/** 1 → "1st", 52 → "52nd", 13 → "13th". */
export function ordinal(n: number): string {
  const r = Math.round(n);
  const tail = r % 100 >= 11 && r % 100 <= 13 ? "th" : ({ 1: "st", 2: "nd", 3: "rd" } as Record<number, string>)[r % 10] ?? "th";
  return `${r}${tail}`;
}

/** An NHANES age band: [40, 49] → "40–49", [80, 120] → "80+". */
export function ageBand([lo, hi]: [number, number]): string {
  return hi >= 120 ? `${lo}+` : `${lo}–${hi}`;
}
