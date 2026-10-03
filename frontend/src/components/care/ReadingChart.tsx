import { useState } from "react";
import { useTranslation } from "react-i18next";

import { READING_UNIT, type Reading, type ReadingKind, type ReadingTarget } from "../../api/care";
import { formatDateTime, formatDayMonth, formatMonth } from "../../lib/format";
import { formatReadingNumber, misses, readingText } from "../../lib/readings";
import { niceTicks, useWidth } from "../insights/TrendChart";

const H = 240;
const PAD = { top: 16, right: 52, bottom: 28, left: 44 };
const DAY = 86_400_000;

/**
 * One kind of home reading over time. The person's own target is drawn as dashed lines (a band when it has both
 * ends); a reading outside it is a filled warm dot. Blood pressure draws its two numbers as two lines.
 * Every reading is also in the table below; the tooltip only adds convenience.
 */
export function ReadingChart({ kind, readings, target }: { kind: ReadingKind; readings: Reading[]; target?: ReadingTarget }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const [ref, width] = useWidth<HTMLDivElement>();
  const [active, setActive] = useState<number | null>(null);
  if (readings.length === 0) return null;

  const pts = [...readings].sort((a, b) => Date.parse(a.taken_at) - Date.parse(b.taken_at))
    .map((r) => ({ t: Date.parse(r.taken_at), v: Number(r.value), v2: r.value2 == null ? null : Number(r.value2), r }));
  const bounds = [target?.low, target?.high, target?.low2, target?.high2].filter((v): v is string => v != null).map(Number);

  let t0 = pts[0].t;
  let t1 = pts[pts.length - 1].t;
  if (t1 - t0 < 2 * DAY) {
    t0 -= DAY;
    t1 += DAY;
  }
  const tPad = (t1 - t0) * 0.04;
  t0 -= tPad;
  t1 += tPad;

  const yValues = [...pts.map((p) => p.v), ...pts.map((p) => p.v2).filter((v): v is number => v != null), ...bounds];
  let y0 = Math.min(...yValues);
  let y1 = Math.max(...yValues);
  const span = y1 - y0 || Math.abs(y1) * 0.1 || 1;
  y0 -= span * 0.15;
  y1 += span * 0.15;
  const ticks = niceTicks(y0, y1);
  y0 = Math.min(y0, ticks[0]);
  y1 = Math.max(y1, ticks[ticks.length - 1]);

  const plotW = width - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;
  const x = (ms: number) => PAD.left + ((ms - t0) / (t1 - t0)) * plotW;
  const y = (v: number) => PAD.top + (1 - (v - y0) / (y1 - y0)) * plotH;
  const path = (get: (p: (typeof pts)[number]) => number | null) =>
    pts.filter((p) => get(p) != null).map((p, i) => `${i ? "L" : "M"}${x(p.t).toFixed(1)},${y(get(p)!).toFixed(1)}`).join(" ");

  const short = t1 - t0 < 120 * DAY;
  const xTicks = [pts[0].t, ...(pts.length > 2 ? [(pts[0].t + pts[pts.length - 1].t) / 2] : []), pts[pts.length - 1].t]
    .filter((ms, i, all) => i === 0 || ms !== all[i - 1]);
  const xLabel = (ms: number) => (short
    ? formatDayMonth(ms, lang)
    : formatMonth(new Date(ms).toISOString(), lang));

  const band = target?.low != null && target?.high != null && kind !== "bp";
  const a = active == null ? null : pts[active];
  const nearest = (clientX: number, rect: DOMRect) => {
    const px = ((clientX - rect.left) / rect.width) * width;
    let best = 0;
    pts.forEach((p, i) => { if (Math.abs(x(p.t) - px) < Math.abs(x(pts[best].t) - px)) best = i; });
    return best;
  };
  const dot = (p: (typeof pts)[number], which: "value" | "value2") =>
    misses(p.r, target).some((m) => m.which === which) ? "var(--abnormal)" : "var(--ink)";

  return (
    <figure className="relative" ref={ref}>
      <svg width={width} height={H} role="img" aria-label={t("readings.chart_label", { kind: t(`readings.kind_${kind}`) })}
        onPointerMove={(e) => setActive(nearest(e.clientX, e.currentTarget.getBoundingClientRect()))}
        onPointerLeave={() => setActive(null)} className="block touch-pan-y select-none">
        {band && (
          <rect x={PAD.left} width={plotW} y={y(Number(target.high))} fill="var(--normal)" fillOpacity="0.1"
            height={Math.max(y(Number(target.low)) - y(Number(target.high)), 1)} />
        )}
        {ticks.map((v) => (
          <g key={v}>
            <line x1={PAD.left} x2={PAD.left + plotW} y1={y(v)} y2={y(v)} stroke="var(--hairline)" strokeWidth="1" />
            <text x={PAD.left - 6} y={y(v) + 4} textAnchor="end" className="tabular fill-muted text-[11px]">{v}</text>
          </g>
        ))}
        {bounds.map((b) => (
          <g key={b}>
            <line x1={PAD.left} x2={PAD.left + plotW} y1={y(b)} y2={y(b)} stroke="var(--normal)" strokeWidth="1.5"
              strokeDasharray="5 4" />
            <text x={PAD.left + plotW + 5} y={y(b) + 4} className="tabular fill-normal text-[11px]">
              {formatReadingNumber(b, kind)}
            </text>
          </g>
        ))}
        {xTicks.map((ms) => (
          <text key={ms} x={x(ms)} y={H - 8} textAnchor="middle" className="fill-muted text-[11px]">{xLabel(ms)}</text>
        ))}
        {kind === "bp" && (
          <path d={path((p) => p.v2)} fill="none" stroke="var(--ink-muted)" strokeWidth="1.5" strokeLinejoin="round"
            pathLength={1} className="draw" />
        )}
        <path d={path((p) => p.v)} fill="none" stroke="var(--ink)" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round"
          pathLength={1} className="draw" />
        {a && <line x1={x(a.t)} x2={x(a.t)} y1={PAD.top} y2={PAD.top + plotH} stroke="var(--ink-muted)" strokeWidth="1" />}
        {pts.map((p, i) => (
          <g key={p.r.id}>
            {p.v2 != null && (
              <circle cx={x(p.t)} cy={y(p.v2)} r={active === i ? 5 : 3.5} fill={dot(p, "value2")}
                stroke="var(--surface-raised)" strokeWidth="1.5" />
            )}
            <circle cx={x(p.t)} cy={y(p.v)} r={active === i ? 5.5 : 4} fill={dot(p, "value")}
              stroke="var(--surface-raised)" strokeWidth="1.5" />
            <circle cx={x(p.t)} cy={y(p.v)} r="11" fill="transparent" tabIndex={0} role="button" className="outline-none"
              aria-label={`${formatDateTime(p.r.taken_at, lang)}: ${readingText(p.r)} ${READING_UNIT[kind]}`}
              onFocus={() => setActive(i)} onBlur={() => setActive(null)} />
          </g>
        ))}
      </svg>
      {a && (
        <div role="status" className="pointer-events-none absolute z-10 -translate-x-1/2 rounded-md border border-hairline bg-raised px-3 py-2 text-sm shadow-sm"
          style={{ left: Math.min(Math.max(x(a.t), 80), width - 80), top: Math.max(y(a.v) - 72, 0) }}>
          <p className="tabular font-semibold">{readingText(a.r)} <span className="font-normal text-muted">{READING_UNIT[kind]}</span></p>
          <p className="whitespace-nowrap text-muted">
            {formatDateTime(a.r.taken_at, lang)}{a.r.context ? ` · ${t(`readings.context_${a.r.context}`, a.r.context)}` : ""}
          </p>
        </div>
      )}
    </figure>
  );
}
