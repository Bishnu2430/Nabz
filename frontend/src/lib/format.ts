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

// Month names for languages a browser may have no date data for (Chrome writes Odia dates in US English).
const MONTHS: Record<string, string[]> = {
  or: ["ଜାନୁଆରୀ", "ଫେବୃଆରୀ", "ମାର୍ଚ୍ଚ", "ଏପ୍ରିଲ୍", "ମେ", "ଜୁନ୍", "ଜୁଲାଇ", "ଅଗଷ୍ଟ", "ସେପ୍ଟେମ୍ବର", "ଅକ୍ଟୋବର", "ନଭେମ୍ବର",
    "ଡିସେମ୍ବର"],
};

const localeOf = (lang: string) => (lang === "en" ? "en-IN" : `${lang}-IN`);

/** A date in the reader's language: the browser's own wording when it knows the language, our month names when not. */
function dateText(d: Date, lang: string, parts: { day?: boolean; year?: boolean; time?: boolean; utc?: boolean }): string {
  const months = MONTHS[lang];
  if (months && Intl.DateTimeFormat.supportedLocalesOf([localeOf(lang)]).length === 0) {
    const [year, month, day, hour, minute] = parts.utc
      ? [d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate(), d.getUTCHours(), d.getUTCMinutes()]
      : [d.getFullYear(), d.getMonth(), d.getDate(), d.getHours(), d.getMinutes()];
    const text = [parts.day ? String(day) : "", months[month], parts.year ? String(year) : ""].filter(Boolean).join(" ");
    return parts.time ? `${text}, ${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}` : text;
  }
  return new Intl.DateTimeFormat(localeOf(lang), {
    ...(parts.day ? { day: "numeric" } : {}),
    month: "short",
    ...(parts.year ? { year: "numeric" } : {}),
    ...(parts.time ? { hour: "numeric", minute: "2-digit" } : {}),
    ...(parts.utc ? { timeZone: "UTC" } : {}),
  }).format(d);
}

export function formatDate(iso: string | null | undefined, lang: string): string {
  if (!iso) return "";
  // Date-only strings are calendar dates: format them in UTC so they never shift a day.
  const dateOnly = iso.length === 10;
  return dateText(new Date(dateOnly ? `${iso}T00:00:00Z` : iso), lang, { day: true, year: true, utc: dateOnly });
}

/** A moment in the reader's own time zone: "28 Sept 2026, 7:30 am". */
export function formatDateTime(iso: string, lang: string): string {
  return dateText(new Date(iso), lang, { day: true, year: true, time: true });
}

/** Day and month in the reader's time zone, for chart axes: "28 Sept". */
export function formatDayMonth(ms: number, lang: string): string {
  return dateText(new Date(ms), lang, { day: true });
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
  return dateText(new Date(`${iso.slice(0, 10)}T00:00:00Z`), lang, { year: true, utc: true });
}

/** Whole years or months between two ISO dates, for "over 3 years". */
export function spanYears(first: string, last: string): number {
  return (Date.parse(last) - Date.parse(first)) / (365.25 * 24 * 3600 * 1000);
}

/** 1 → "1st", 52 → "52nd", 13 → "13th"; in Hindi "52वें", in Odia "52ତମ". */
export function ordinal(n: number, lang = "en"): string {
  const r = Math.round(n);
  if (lang === "hi") return `${r}वें`;
  if (lang === "or") return `${r}ତମ`;
  const tail = r % 100 >= 11 && r % 100 <= 13 ? "th" : ({ 1: "st", 2: "nd", 3: "rd" } as Record<number, string>)[r % 10] ?? "th";
  return `${r}${tail}`;
}

/** An NHANES age band: [40, 49] → "40–49", [80, 120] → "80+". */
export function ageBand([lo, hi]: [number, number]): string {
  return hi >= 120 ? `${lo}+` : `${lo}–${hi}`;
}

/** The fields every result shape shares (Result, ResultBrief). */
export interface ValueLike {
  test_code: string;
  test_name: string;
  short_name: string;
  value: string;
  unit: string | null;
  decimals: number;
  status: string;
  ref_low: string | null;
  ref_high: string | null;
}

/** How far a value is outside its range, as a fraction of the bound it crossed; null when inside or no range. */
export function deviation(v: ValueLike): { side: "above" | "below"; fraction: number; bound: string } | null {
  const value = Number(v.value);
  if (v.ref_high != null && value > Number(v.ref_high)) {
    const hi = Number(v.ref_high);
    return { side: "above", fraction: hi ? value / hi - 1 : 0, bound: formatComputed(v.ref_high) };
  }
  if (v.ref_low != null && value < Number(v.ref_low)) {
    const lo = Number(v.ref_low);
    return { side: "below", fraction: lo ? 1 - value / lo : 0, bound: formatComputed(v.ref_low) };
  }
  return null;
}

/** A value with its unit at the test's precision: "1.62 mg/dL". */
export function formatWithUnit(v: Pick<ValueLike, "value" | "decimals" | "unit">): string {
  const unit = formatUnit(v.unit);
  return unit ? `${formatValue(v.value, v.decimals)} ${unit}` : formatValue(v.value, v.decimals);
}

/** Percentage without a sign, one decimal below 10: "25 %", "4.5 %". */
export function formatShare(fraction: number): string {
  const pct = Math.abs(fraction) * 100;
  return `${pct >= 10 ? pct.toFixed(0) : pct.toFixed(1)} %`;
}
