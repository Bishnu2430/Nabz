import type { ObsStatus } from "../../api/types";
import { STATUS_COLOR } from "../insights/StatusMark";

export interface SparkPoint {
  date: string;
  value: number;
  status: ObsStatus;
}

/**
 * A small chart of one test over time: the latest range as a band, each result as a dot in its status colour.
 * Decorative (aria-hidden): the value, the change and the dates are written beside it.
 */
export function Sparkline({ points, low, high, width = 180, height = 44 }: {
  points: SparkPoint[];
  low: number | null;
  high: number | null;
  width?: number;
  height?: number;
}) {
  if (points.length === 0) return null;
  const values = points.map((p) => p.value);
  const lo = Math.min(...values, low ?? Infinity);
  const hi = Math.max(...values, high ?? -Infinity);
  const pad = (hi - lo || Math.abs(hi) || 1) * 0.15;
  const y0 = lo - pad;
  const y1 = hi + pad;
  const t0 = Date.parse(points[0].date);
  const t1 = Date.parse(points[points.length - 1].date);
  const x = (d: string) => (points.length === 1 || t1 === t0 ? width / 2 : 6 + ((Date.parse(d) - t0) / (t1 - t0)) * (width - 12));
  const y = (v: number) => height - 4 - ((v - y0) / (y1 - y0)) * (height - 8);
  const bandTop = high != null ? y(high) : 0;
  const bandBottom = low != null ? y(low) : height;

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden="true" className="overflow-visible">
      {(low != null || high != null) && (
        <rect x="0" y={bandTop} width={width} height={Math.max(bandBottom - bandTop, 1)} fill="var(--normal)"
          fillOpacity="0.14" />
      )}
      {points.length > 1 && (
        <polyline points={points.map((p) => `${x(p.date)},${y(p.value)}`).join(" ")} fill="none" stroke="var(--ink)"
          strokeOpacity="0.45" strokeWidth="1.5" strokeLinejoin="round" />
      )}
      {points.map((p, i) => (
        <circle key={p.date + i} cx={x(p.date)} cy={y(p.value)} r={i === points.length - 1 ? 4 : 2.6}
          fill={STATUS_COLOR[p.status]} stroke="var(--surface-raised)" strokeWidth="1" />
      ))}
    </svg>
  );
}
