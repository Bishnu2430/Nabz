import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import type { Result, TestInfo } from "../../api/types";
import { formatDate, formatMonth, formatUnit, formatValue } from "../../lib/format";
import { STATUS_COLOR, isAbnormal } from "./StatusMark";

const H = 260;
const PAD = { top: 18, right: 64, bottom: 30, left: 48 };
const DAY = 24 * 3600 * 1000;
const YEAR = 365.25 * DAY;

/** Round tick values inside [lo, hi]: the 1-2-2.5-5 step whose tick count is closest to `target` (more wins a tie). */
export function niceTicks(lo: number, hi: number, target = 4): number[] {
  if (hi <= lo) return [lo];
  const mag = 10 ** Math.floor(Math.log10((hi - lo) / target));
  const count = (step: number) => Math.floor(hi / step + 1e-9) - Math.ceil(lo / step - 1e-9) + 1;
  const steps = [0.5, 1, 2, 2.5, 5, 10, 20].map((m) => m * mag);
  const step = steps.reduce((best, s) => {
    const d = Math.abs(count(s) - target) - Math.abs(count(best) - target);
    return d < 0 || (d === 0 && count(s) > count(best)) ? s : best;
  });
  const ticks: number[] = [];
  for (let v = Math.ceil(lo / step - 1e-9) * step; v <= hi + step * 1e-9; v += step) ticks.push(Number(v.toPrecision(12)));
  return ticks;
}

function useWidth<T extends HTMLElement>(fallback = 640) {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(fallback);
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(([entry]) => setWidth(Math.max(280, Math.round(entry.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return [ref, width] as const;
}

/**
 * One test over time (a single series: no legend; the heading names it).
 * - The latest report's range is a light band; the value line is 2 px ink with status-coloured points.
 * - A segment where the value came back into range is drawn in gold (kintsugi, doc 12 §5.3).
 * - A confirmed trend adds its fitted line, and a projection (dashed: it is not data) to the range limit.
 * Every value is also in the table below the chart; the tooltip only adds convenience.
 */
export function TrendChart({ results, test }: { results: Result[]; test: TestInfo }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const [ref, width] = useWidth<HTMLDivElement>();
  const [active, setActive] = useState<number | null>(null);
  if (results.length === 0) return null;

  const pts = results.map((r) => ({ t: Date.parse(r.date), v: Number(r.value), r }));
  const latest = results[results.length - 1];
  const low = latest.ref_low == null ? null : Number(latest.ref_low);
  const high = latest.ref_high == null ? null : Number(latest.ref_high);
  const trend = latest.trend?.confirmed ? latest.trend : null;
  const projection = trend?.projection ?? null;

  let t0 = pts[0].t;
  let t1 = Math.max(pts[pts.length - 1].t, projection ? Date.parse(projection.on) : 0);
  if (t1 - t0 < 60 * DAY) {
    t0 -= 90 * DAY;
    t1 += 90 * DAY;
  }
  const tPad = (t1 - t0) * 0.04;
  t0 -= tPad;
  t1 += tPad;

  const yValues = [...pts.map((p) => p.v), low, high, projection?.value].filter((v): v is number => v != null);
  let y0 = Math.min(...yValues);
  let y1 = Math.max(...yValues);
  const ySpan = y1 - y0 || Math.abs(y1) * 0.2 || 1;
  y0 -= ySpan * 0.15;
  y1 += ySpan * 0.15;
  if (Math.min(...yValues) >= 0) y0 = Math.max(0, y0);
  const ticks = niceTicks(y0, y1);
  y0 = Math.min(y0, ticks[0]);
  y1 = Math.max(y1, ticks[ticks.length - 1]);

  const plotW = width - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;
  const x = (ms: number) => PAD.left + ((ms - t0) / (t1 - t0)) * plotW;
  const y = (v: number) => PAD.top + (1 - (v - y0) / (y1 - y0)) * plotH;

  // x ticks: 1 January of each year in view, or the first and last result when the span is short
  const years: number[] = [];
  for (let yr = new Date(t0).getUTCFullYear() + 1; Date.UTC(yr, 0, 1) < t1; yr++) years.push(Date.UTC(yr, 0, 1));
  const xTicks = years.length >= 2 ? years.filter((_, i) => years.length <= 6 || i % 2 === 0) : [pts[0].t, pts[pts.length - 1].t];
  const xLabel = (ms: number) => (years.length >= 2 ? String(new Date(ms).getUTCFullYear()) : formatMonth(new Date(ms).toISOString(), lang));

  const line = pts.map((p, i) => `${i ? "L" : "M"}${x(p.t).toFixed(1)},${y(p.v).toFixed(1)}`).join(" ");
  const fitted = trend && (() => {
    const tf = Date.parse(trend.first);
    const at = (ms: number) => trend.intercept + trend.slope_per_year * ((ms - tf) / YEAR);
    const tl = Date.parse(trend.last);
    return { from: [x(tf), y(at(tf))], to: [x(tl), y(at(tl))] };
  })();

  const decimals = test.decimals;
  const unit = formatUnit(test.unit);
  const a = active == null ? null : pts[active];
  const nearest = (clientX: number, rect: DOMRect) => {
    const px = ((clientX - rect.left) / rect.width) * width;
    let best = 0;
    pts.forEach((p, i) => { if (Math.abs(x(p.t) - px) < Math.abs(x(pts[best].t) - px)) best = i; });
    return best;
  };

  return (
    <figure className="relative" ref={ref}>
      <svg width={width} height={H} role="img" aria-label={t("history.chart_label", { test: test.name })}
        onPointerMove={(e) => setActive(nearest(e.clientX, e.currentTarget.getBoundingClientRect()))}
        onPointerLeave={() => setActive(null)} className="block touch-pan-y select-none">
        {/* range band */}
        {(low != null || high != null) && (
          <g>
            <rect x={PAD.left} width={plotW} y={y(high ?? y1)} height={Math.max(y(low ?? y0) - y(high ?? y1), 1)}
              fill="var(--normal)" fillOpacity="0.1" />
            <text x={PAD.left + 6} y={y(high ?? y1) + 13} className="fill-muted text-[11px]">
              {t("history.range_band")}
            </text>
          </g>
        )}
        {/* recessive grid and axes */}
        {ticks.map((v) => (
          <g key={v}>
            <line x1={PAD.left} x2={PAD.left + plotW} y1={y(v)} y2={y(v)} stroke="var(--hairline)" strokeWidth="1" />
            <text x={PAD.left - 6} y={y(v) + 4} textAnchor="end" className="tabular fill-muted text-[11px]">
              {formatValue(v, Math.min(decimals, 2))}
            </text>
          </g>
        ))}
        {xTicks.map((ms) => (
          <text key={ms} x={x(ms)} y={H - 8} textAnchor="middle" className="fill-muted text-[11px]">{xLabel(ms)}</text>
        ))}
        {/* confirmed trend: fitted line, then the projection (dashed because it is not data) */}
        {fitted && (
          <line x1={fitted.from[0]} y1={fitted.from[1]} x2={fitted.to[0]} y2={fitted.to[1]}
            stroke="var(--ink-muted)" strokeWidth="1.5" strokeOpacity="0.7" />
        )}
        {fitted && projection && (
          <g>
            <line x1={fitted.to[0]} y1={fitted.to[1]} x2={x(Date.parse(projection.on))} y2={y(projection.value)}
              stroke="var(--ink-muted)" strokeWidth="1.5" strokeDasharray="5 4" />
            <circle cx={x(Date.parse(projection.on))} cy={y(projection.value)} r="4" fill="var(--surface-raised)"
              stroke="var(--ink-muted)" strokeWidth="1.5" />
            <text x={x(Date.parse(projection.on))} y={y(projection.value) - 9} textAnchor="middle" className="fill-muted text-[11px]">
              {formatMonth(projection.on, lang)}
            </text>
          </g>
        )}
        {/* the values */}
        <path d={line} fill="none" stroke="var(--ink)" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
        {pts.slice(1).map((p, i) => isAbnormal(pts[i].r.status) && p.r.status === "normal" && (
          <line key={`k${i}`} x1={x(pts[i].t)} y1={y(pts[i].v)} x2={x(p.t)} y2={y(p.v)}
            stroke="var(--gold)" strokeWidth="3.5" strokeLinecap="round" />
        ))}
        {a && <line x1={x(a.t)} x2={x(a.t)} y1={PAD.top} y2={PAD.top + plotH} stroke="var(--ink-muted)" strokeWidth="1" />}
        {pts.map((p, i) => (
          <g key={p.r.observation_id}>
            <circle cx={x(p.t)} cy={y(p.v)} r={active === i ? 6 : 4.5} fill={STATUS_COLOR[p.r.status]}
              stroke="var(--surface-raised)" strokeWidth="2" />
            <circle cx={x(p.t)} cy={y(p.v)} r="12" fill="transparent" tabIndex={0} role="button"
              aria-label={`${formatDate(p.r.date, lang)}: ${formatValue(p.r.value, decimals)} ${unit}, ${t(`result_status.${p.r.status}`)}`}
              onFocus={() => setActive(i)} onBlur={() => setActive(null)} className="outline-none" />
          </g>
        ))}
        {/* direct label on the latest value only */}
        <text x={x(pts[pts.length - 1].t) + (projection ? 0 : 10)} y={y(pts[pts.length - 1].v) + (projection ? 20 : 4)}
          textAnchor={projection ? "middle" : "start"} className="tabular fill-ink text-[12px] font-medium">
          {formatValue(latest.value, decimals)}
        </text>
      </svg>
      {a && (
        <div role="status" className="pointer-events-none absolute z-10 -translate-x-1/2 rounded-md border border-hairline bg-raised px-3 py-2 text-sm shadow-sm"
          style={{ left: Math.min(Math.max(x(a.t), 70), width - 70), top: Math.max(y(a.v) - 72, 0) }}>
          <p className="tabular font-semibold">{formatValue(a.r.value, decimals)} <span className="font-normal text-muted">{unit}</span></p>
          <p className="text-muted">{formatDate(a.r.date, lang)} · {t(`result_status.${a.r.status}`)}</p>
        </div>
      )}
    </figure>
  );
}
