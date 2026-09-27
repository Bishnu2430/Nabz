import clsx from "clsx";

/**
 * Ensō: a single brush circle, left open. While `active`, the stroke is drawn and redrawn;
 * when done it rests as a complete brush mark. Reduced-motion users see the resting mark.
 */
export function Enso({ active = true, size = 120, label, className }: {
  active?: boolean;
  size?: number;
  label: string;
  className?: string;
}) {
  return (
    <div role="status" aria-live="polite" className={clsx("inline-flex flex-col items-center gap-3", className)}>
      <svg width={size} height={size} viewBox="0 0 100 100" aria-hidden="true" className="text-ink">
        {/* two overlapping strokes of different width read as one brush mark with a dry edge */}
        <path
          d="M72 18 C 50 6, 16 16, 12 46 C 8 76, 38 94, 64 86 C 86 79, 94 56, 86 36"
          fill="none"
          stroke="currentColor"
          strokeWidth="7"
          strokeLinecap="round"
          pathLength={100}
          className={clsx("enso-stroke", active && "enso-active")}
        />
        <path
          d="M70 20 C 50 9, 19 18, 15 46 C 12 73, 39 90, 63 83"
          fill="none"
          stroke="currentColor"
          strokeOpacity="0.35"
          strokeWidth="2"
          strokeLinecap="round"
          pathLength={100}
          className={clsx("enso-stroke", active && "enso-active")}
        />
      </svg>
      <span className="text-muted">{label}</span>
    </div>
  );
}
