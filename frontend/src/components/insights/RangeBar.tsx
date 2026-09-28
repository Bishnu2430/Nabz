import type { ObsStatus } from "../../api/types";
import { STATUS_COLOR } from "./StatusMark";

/**
 * Where a value sits against its range: a light band for the range and a mark for the value. Decorative only
 * (aria-hidden): the value, the range and the status word beside it carry the information.
 */
export function RangeBar({ value, low, high, status }: {
  value: number;
  low: number | null;
  high: number | null;
  status: ObsStatus;
}) {
  if (low == null && high == null) return null;
  let lo: number;
  let hi: number;
  if (low != null && high != null) {
    const span = high - low || Math.abs(high) || 1;
    lo = low - span * 0.5;
    hi = high + span * 0.5;
  } else if (high != null) {
    lo = 0;
    hi = high * 1.6;
  } else {
    lo = 0;
    hi = (low as number) * 2.2;
  }
  const W = 120;
  const H = 12;
  const x = (v: number) => Math.min(Math.max(((v - lo) / (hi - lo)) * W, 0), W);
  const bandFrom = low != null ? x(low) : 0;
  const bandTo = high != null ? x(high) : W;
  const vx = x(value);
  const outside = value < lo || value > hi;

  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} aria-hidden="true" className="shrink-0 overflow-visible">
      <rect x="0" y={H / 2 - 1} width={W} height="2" rx="1" fill="var(--hairline)" />
      <rect x={bandFrom} y={H / 2 - 3} width={Math.max(bandTo - bandFrom, 2)} height="6" rx="3"
        fill="var(--normal)" fillOpacity="0.25" />
      {outside ? (
        <path d={vx <= 0 ? `M6 1 L0 6 L6 11 Z` : `M${W - 6} 1 L${W} 6 L${W - 6} 11 Z`} fill={STATUS_COLOR[status]} />
      ) : (
        <circle cx={vx} cy={H / 2} r="4.5" fill={STATUS_COLOR[status]} stroke="var(--surface-raised)" strokeWidth="2" />
      )}
    </svg>
  );
}
