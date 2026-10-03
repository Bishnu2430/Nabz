import clsx from "clsx";
import type { ReactNode } from "react";

/**
 * One family of line icons: 24-unit grid, 1.6 stroke, round ends, no fills (doc 12 §5). They take the text colour,
 * so they follow both themes. Icons are always beside a word, never instead of one, so they are hidden from
 * screen readers.
 */
const PATHS: Record<string, ReactNode> = {
  family: <><circle cx="8" cy="7.5" r="2.8" /><circle cx="16.5" cy="9" r="2.3" /><path d="M3 19c0-3 2.2-5.2 5-5.2s5 2.2 5 5.2M13.2 19c.2-2.6 1.6-4.4 3.3-4.4 2 0 3.5 1.9 3.5 4.4" /></>,
  person: <><circle cx="12" cy="8" r="3.4" /><path d="M5 20c0-3.9 3.1-6.5 7-6.5s7 2.6 7 6.5" /></>,
  report: <><path d="M7 3h7l4 4v14H7z" /><path d="M14 3v4h4M10 12h5M10 15.5h5M10 9h2" /></>,
  upload: <><path d="M12 15V4M7.5 8.5 12 4l4.5 4.5" /><path d="M5 14v5h14v-5" /></>,
  play: <path d="M8 5.5v13l10.5-6.5z" />,
  tests: <><path d="M9 6h11M9 12h11M9 18h11" /><circle cx="5" cy="6" r="1.2" /><circle cx="5" cy="12" r="1.2" /><circle cx="5" cy="18" r="1.2" /></>,
  summary: <><rect x="6" y="4.5" width="12" height="16" rx="1.5" /><path d="M9.5 3h5v3h-5zM9 11h6M9 14.5h6M9 18h3" /></>,
  compare: <><rect x="3.5" y="5" width="7" height="14" rx="1.2" /><rect x="13.5" y="5" width="7" height="14" rx="1.2" /><path d="M6 9.5h2M6 12.5h2M16 9.5h2M16 12.5h2" /></>,
  readings: <><path d="M3 13h3.5l2-5 3.5 10 2.5-7 1.5 2H21" /></>,
  card: <><rect x="3" y="5.5" width="18" height="13" rx="2" /><path d="M7.5 10.5h3M9 9v3M14 10h3.5M14 13.5h3.5M7 15.5h4" /></>,
  bell: <><path d="M6 10a6 6 0 1 1 12 0c0 5 2 6 2 6H4s2-1 2-6Z" /><path d="M10 19.5a2 2 0 0 0 4 0" /></>,
  calendar: <><rect x="3.5" y="5" width="17" height="15" rx="2" /><path d="M3.5 10h17M8 3v4M16 3v4" /></>,
  mail: <><rect x="3" y="5.5" width="18" height="13" rx="2" /><path d="m3.5 7 8.5 6.5L20.5 7" /></>,
  share: <><circle cx="6" cy="12" r="2.5" /><circle cx="18" cy="6" r="2.5" /><circle cx="18" cy="18" r="2.5" /><path d="m8.2 10.9 7.6-3.8M8.2 13.1l7.6 3.8" /></>,
  shield: <><path d="M12 3 5 6v5.5c0 4.3 3 7.8 7 9.5 4-1.7 7-5.2 7-9.5V6z" /><path d="m9 12 2.2 2.2L15.5 10" /></>,
  lock: <><rect x="5" y="10.5" width="14" height="10" rx="2" /><path d="M8 10.5V8a4 4 0 0 1 8 0v2.5M12 14.5v2.5" /></>,
  chat: <><path d="M4 5.5h16v10H10l-4.5 3.5v-3.5H4z" /><path d="M8 9.5h8M8 12.5h5" /></>,
  body: <><circle cx="12" cy="4.5" r="2.2" /><path d="M7 9h10M12 9v6M12 15l-3 6M12 15l3 6M7 9l-1.5 6M17 9l1.5 6" /></>,
  film: <><rect x="3" y="3" width="18" height="18" rx="2" /><path d="M9 7.5a1.5 1.5 0 1 0-1 2.6L14 16a1.5 1.5 0 1 0 2.6-1L10.6 9A1.5 1.5 0 0 0 9 7.5Z" /></>,
  settings: <><circle cx="12" cy="12" r="3" /><path d="M12 2.5v2.6M12 18.9v2.6M4.4 4.4l1.8 1.8M17.8 17.8l1.8 1.8M2.5 12h2.6M18.9 12h2.6M4.4 19.6l1.8-1.8M17.8 6.2l1.8-1.8" /></>,
  globe: <><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3c3 3.5 3 14.5 0 18M12 3c-3 3.5-3 14.5 0 18" /></>,
  download: <><path d="M12 4v11M7.5 10.5 12 15l4.5-4.5" /><path d="M5 19h14" /></>,
  trash: <><path d="M4.5 7h15M9.5 7V4.5h5V7M6.5 7l1 13h9l1-13M10.5 11v5M13.5 11v5" /></>,
  check: <path d="m5 12.5 4.5 4.5L19 7.5" />,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v5.5M12 7.8v.2" /></>,
  alert: <><path d="M12 4 2.8 19.5h18.4z" /><path d="M12 10v4.5M12 17.2v.2" /></>,
  heart: <path d="M12 20s-7.5-4.6-7.5-10.2A4.3 4.3 0 0 1 12 7.4a4.3 4.3 0 0 1 7.5 2.4C19.5 15.4 12 20 12 20Z" />,
  drop: <path d="M12 3.5s6 6.6 6 10.8a6 6 0 0 1-12 0C6 10.1 12 3.5 12 3.5Z" />,
  scale: <><rect x="4" y="4" width="16" height="16" rx="3" /><path d="M8.5 9.5a5 5 0 0 1 7 0L13.5 12h-3z" /></>,
  pulse: <path d="M3 12h4l2-5 4 10 2-5h6" />,
  thermometer: <><path d="M10 13.5V5a2 2 0 0 1 4 0v8.5a4 4 0 1 1-4 0Z" /><path d="M12 9v7" /></>,
  lungs: <><path d="M12 4v7M12 11c-1.5 1-2.5 1.2-3.5 1M12 11c1.5 1 2.5 1.2 3.5 1" /><path d="M8.5 7.5C5.5 8 4 12 4 16.5c0 2 1.2 3 3 3s3-1.5 3-4V9" /><path d="M15.5 7.5c3 .5 4.5 4.5 4.5 9 0 2-1.2 3-3 3s-3-1.5-3-4V9" /></>,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3.5 2" /></>,
  printer: <><path d="M7 8V3.5h10V8" /><rect x="3.5" y="8" width="17" height="8" rx="1.5" /><path d="M7 13.5h10V20H7z" /></>,
  link: <><path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7L11.5 6.8" /><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1.5-1.5" /></>,
  search: <><circle cx="10.5" cy="10.5" r="6" /><path d="m15 15 5 5" /></>,
  trend: <><path d="M3 17l5-5 4 3 8-9" /><path d="M15 6h5v5" /></>,
  book: <><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5z" /><path d="M4 20.5A2.5 2.5 0 0 1 6.5 18H20v3H6.5" /></>,
  pen: <><path d="M15.5 4.5l4 4L9 19H5v-4z" /><path d="m13.5 6.5 4 4" /></>,
  pill: <><rect x="3.5" y="8.5" width="17" height="7" rx="3.5" transform="rotate(-35 12 12)" /><path d="m9.5 8 5 8" /></>,
  stethoscope: <><path d="M6 3v6a4 4 0 0 0 8 0V3M10 13v3a5 5 0 0 0 10 0v-2" /><circle cx="20" cy="12" r="2" /></>,
  phone: <path d="M6.5 3.5h3l1.5 4.5-2 1.5a11 11 0 0 0 5.5 5.5l1.5-2 4.5 1.5v3a2 2 0 0 1-2 2A16 16 0 0 1 4.5 5.5a2 2 0 0 1 2-2Z" />,
  plus: <path d="M12 5v14M5 12h14" />,
  arrow: <path d="M5 12h14M13 6l6 6-6 6" />,
  eye: <><path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z" /><circle cx="12" cy="12" r="2.8" /></>,
  key: <><circle cx="8" cy="15" r="3.5" /><path d="m10.5 12.5 8-8M16 7l2.5 2.5M14 9l2 2" /></>,
  devices: <><rect x="3" y="5" width="13" height="10" rx="1.5" /><path d="M7 19h5M9.5 15v4" /><rect x="17.5" y="9" width="4" height="10" rx="1" /></>,
  door: <><path d="M14 4H6v16h8" /><path d="M11 12h10M17.5 8.5 21 12l-3.5 3.5" /></>,
  sample: <><path d="M9 3h6M10 3v6L5 19a1.5 1.5 0 0 0 1.3 2h11.4a1.5 1.5 0 0 0 1.3-2L14 9V3" /><path d="M7.5 15h9" /></>,
  // organ systems (data/catalogue/organ_systems.csv)
  organ_blood: <><path d="M12 3.5s6 6.6 6 10.8a6 6 0 0 1-12 0C6 10.1 12 3.5 12 3.5Z" /><path d="M9.5 14.5a2.5 2.5 0 0 0 2.5 2.5" /></>,
  organ_heart: <><path d="M12 20s-7.5-4.6-7.5-10.2A4.3 4.3 0 0 1 12 7.4a4.3 4.3 0 0 1 7.5 2.4C19.5 15.4 12 20 12 20Z" /><path d="M7 12.5h2.5l1.2-2 1.8 4 1.2-2H17" /></>,
  organ_liver: <path d="M3.5 9.5C3.5 6.5 6.5 5 11 5h7c2.2 0 3.3 1.7 2.2 3.7C18.6 12 14.5 16.5 9.5 18 5.5 19 3.5 14 3.5 9.5Z" />,
  organ_kidney: <><path d="M13 5.5C11 2.8 5.5 3.6 5 8.6c-.4 4.4 1.4 9 5 9.9 2.5.6 3.4-1.4 2.9-3.4-.4-1.7 1.7-2.6 1.7-4.8 0-1.7-.6-3.3-1.6-4.8Z" /><path d="M14.5 10.5h3.5l1.5 3" /></>,
  organ_urinary: <><path d="M6 10c0-3 2.7-4.5 6-4.5S18 7 18 10c0 4-2.6 7-6 7s-6-3-6-7Z" /><path d="M12 17v3.5M8.5 5.5 7 3M15.5 5.5 17 3" /></>,
  organ_pancreas: <><path d="M12 3.5 19.5 7.8v8.4L12 20.5l-7.5-4.3V7.8z" /><path d="M4.5 7.8 12 12l7.5-4.2M12 12v8.5" /></>,
  organ_thyroid: <><path d="M12 8.5v8" /><path d="M12 10c-1.6-3.3-6.6-3.6-7 .4-.4 3.7 2.6 6.4 7 5.1M12 10c1.6-3.3 6.6-3.6 7 .4.4 3.7-2.6 6.4-7 5.1" /></>,
  organ_bone: <><path d="m8.5 9.5 6 6" /><path d="M8.6 9.4a2.2 2.2 0 1 1-2.9-2.6 2.2 2.2 0 1 1 3.4-1.4 2.2 2.2 0 0 1-.5 4ZM15.4 14.6a2.2 2.2 0 1 1 2.9 2.6 2.2 2.2 0 1 1-3.4 1.4 2.2 2.2 0 0 1 .5-4Z" /></>,
  organ_immune: <><path d="M12 3 5 6v5.5c0 4.3 3 7.8 7 9.5 4-1.7 7-5.2 7-9.5V6z" /><path d="M12 8.5v7M8.5 12h7" /></>,
  organ_prostate: <><circle cx="12" cy="12" r="6.5" /><circle cx="12" cy="12" r="2" /></>,
};

export type IconName = keyof typeof PATHS;

/** An organ system's mark; a plain circle for one the set doesn't draw. */
export const organIcon = (code: string): IconName => (`organ_${code}` in PATHS ? `organ_${code}` : "organ_prostate");

export function Icon({ name, size = 20, className, strokeWidth = 1.6 }: {
  name: IconName;
  size?: number;
  className?: string;
  strokeWidth?: number;
}) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={strokeWidth}
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className={clsx("shrink-0", className)}>
      {PATHS[name]}
    </svg>
  );
}

/** An icon set in a small square seal, the way a heading carries its mark. */
export function IconSeal({ name, className, size = 18 }: { name: IconName; className?: string; size?: number }) {
  return (
    <span aria-hidden="true" className={clsx("icon-seal inline-grid shrink-0 place-items-center rounded-lg", className)}>
      <Icon name={name} size={size} />
    </span>
  );
}
