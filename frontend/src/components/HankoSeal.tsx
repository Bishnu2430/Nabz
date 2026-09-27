import clsx from "clsx";

/**
 * The seal stamped when a person confirms the values: the human-review gate.
 * The mark is the Nabz pulse line, not a character (doc 12 §5.4). `stamped` plays the press once.
 */
export function HankoSeal({ stamped, size = 96, className }: { stamped: boolean; size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      aria-hidden="true"
      className={clsx("text-accent", stamped ? "hanko-stamped" : "opacity-0", className)}
    >
      <defs>
        {/* uneven ink: the seal paste never prints perfectly */}
        <filter id="hanko-ink" x="-10%" y="-10%" width="120%" height="120%">
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="7" result="noise" />
          <feColorMatrix in="noise" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -1.1 1.4" result="mask" />
          <feComposite in="SourceGraphic" in2="mask" operator="in" />
        </filter>
      </defs>
      <g filter="url(#hanko-ink)" transform="rotate(-4 50 50)">
        <rect x="8" y="8" width="84" height="84" rx="10" fill="none" stroke="currentColor" strokeWidth="6" />
        <rect x="16" y="16" width="68" height="68" rx="5" fill="currentColor" />
        <path
          d="M22 54h14l6-18 10 32 7-21 5 7h14"
          fill="none"
          stroke="var(--surface-raised)"
          strokeWidth="6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </g>
    </svg>
  );
}
