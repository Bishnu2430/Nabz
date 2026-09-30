import clsx from "clsx";
import type { KeyboardEvent } from "react";

import type { ObsStatus } from "../../api/types";
import { STATUS_COLOR, isAbnormal } from "../insights/StatusMark";
import { BODY_HALF_2D, ORGAN_ORDER, SHAPES_2D, type OrganCode, type OrganStatus } from "./organs";

/**
 * The ink body in 2D: the fallback when WebGL 2 is unavailable (FR-31), the landing-page figure, and the
 * print view. Organs with results are tinted with their worst status; the rest stay as faint ink.
 */
export function BodyDiagram({ statuses, selected, onSelect, labels, className, decorative = false }: {
  statuses: OrganStatus;
  selected?: OrganCode | null;
  onSelect?: (code: OrganCode) => void;
  /** Accessible name per organ, e.g. "Liver: high". Required unless decorative. */
  labels?: Partial<Record<OrganCode, string>>;
  className?: string;
  decorative?: boolean;
}) {
  const shown = ORGAN_ORDER.filter((code) => code !== "prostate" || statuses.prostate);

  return (
    <svg viewBox="0 0 240 530" className={clsx("h-auto w-full", className)} aria-hidden={decorative || undefined}
      role={decorative ? undefined : "group"}>
      <defs>
        <filter id="ink-bleed" x="-5%" y="-5%" width="110%" height="110%">
          <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="2" seed="3" result="n" />
          <feDisplacementMap in="SourceGraphic" in2="n" scale="1.6" />
        </filter>
      </defs>

      {/* rice paper and a single ink contour */}
      <g filter="url(#ink-bleed)">
        {[false, true].map((mirrored) => (
          <g key={String(mirrored)} transform={mirrored ? "translate(240 0) scale(-1 1)" : undefined}>
            <path d={`${BODY_HALF_2D} L120 76 Z`} fill="var(--surface-raised)" stroke="none" />
            <path d={BODY_HALF_2D} fill="none" stroke="var(--ink)" strokeWidth="2.2" strokeLinecap="round"
              strokeLinejoin="round" opacity="0.85" />
          </g>
        ))}
        <ellipse cx="120" cy="50" rx="25" ry="31" fill="var(--surface-raised)" stroke="var(--ink)" strokeWidth="2.2"
          opacity="0.95" />
      </g>

      {shown.map((code) => (
        <OrganShape key={code} code={code} status={statuses[code]} selected={selected === code}
          label={labels?.[code]} onSelect={decorative ? undefined : onSelect} />
      ))}
    </svg>
  );
}

function OrganShape({ code, status, selected, label, onSelect }: {
  code: OrganCode;
  status?: ObsStatus;
  selected: boolean;
  label?: string;
  onSelect?: (code: OrganCode) => void;
}) {
  const colour = status ? STATUS_COLOR[status] : "var(--ink)";
  const opacity = status ? (isAbnormal(status) ? 0.9 : 0.7) : 0.12;
  const interactive = Boolean(onSelect && status);
  const keyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onSelect?.(code);
    }
  };

  return (
    <g
      data-organ={code}
      role={interactive ? "button" : undefined}
      tabIndex={interactive ? 0 : undefined}
      aria-label={interactive ? label : undefined}
      aria-pressed={interactive ? selected : undefined}
      onClick={interactive ? () => onSelect?.(code) : undefined}
      onKeyDown={interactive ? keyDown : undefined}
      className={clsx(interactive && "cursor-pointer outline-none [&:focus-visible>.halo]:opacity-100")}
    >
      {interactive && label && <title>{label}</title>}
      {SHAPES_2D[code].map((s, i) =>
        s.line ? (
          <g key={i}>
            {/* a wide invisible stroke makes thin vessels easy to tap */}
            {interactive && <path d={s.d} fill="none" stroke="transparent" strokeWidth="12" />}
            <path className="halo opacity-0 transition-opacity" d={s.d} fill="none" stroke="var(--focus)"
              strokeWidth="7" strokeLinecap="round" style={{ opacity: selected ? 0.35 : undefined }} />
            <path d={s.d} fill="none" stroke={colour} strokeOpacity={opacity} strokeLinecap="round"
              strokeWidth={code === "bone" ? 4 : 2} />
          </g>
        ) : (
          <g key={i}>
            <path className="halo opacity-0 transition-opacity" d={s.d} fill="none" stroke="var(--focus)"
              strokeWidth="5" style={{ opacity: selected ? 0.5 : undefined }} />
            <path d={s.d} fill={colour} fillOpacity={opacity} stroke={status ? colour : "var(--ink)"}
              strokeOpacity={status ? 1 : 0.25} strokeWidth="1.2" />
          </g>
        ),
      )}
    </g>
  );
}
