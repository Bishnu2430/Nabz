import { useCallback, useEffect, useState } from "react";

export type Theme = "light" | "dark";

const KEY = "nabz.theme";

function systemTheme(): Theme {
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function savedTheme(): Theme | null {
  try {
    const t = localStorage.getItem(KEY);
    return t === "light" || t === "dark" ? t : null;
  } catch {
    return null;
  }
}

/**
 * Sumi-e (light) or urushi (dark). Follows the system until the user picks one. The new theme spreads from the
 * switch where the browser supports view transitions; elsewhere the colours cross-fade.
 */
export function useTheme(): [Theme, (origin?: { x: number; y: number }) => void] {
  const [theme, setTheme] = useState<Theme>(() => savedTheme() ?? systemTheme());

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const toggle = useCallback((origin?: { x: number; y: number }) => {
    const root = document.documentElement;
    const next: Theme = (root.dataset.theme ?? theme) === "light" ? "dark" : "light";
    const apply = () => {
      root.dataset.theme = next; // set at once so a view transition captures the new look
      setTheme(next);
      try {
        localStorage.setItem(KEY, next);
      } catch {
        /* storage unavailable: the choice lasts for this visit */
      }
    };
    const calm = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    const doc = document as Document & { startViewTransition?: (update: () => void) => unknown };
    if (calm) apply();
    else if (doc.startViewTransition && origin && typeof origin.x === "number") {
      root.style.setProperty("--theme-x", `${origin.x}px`);
      root.style.setProperty("--theme-y", `${origin.y}px`);
      doc.startViewTransition(apply);
    } else {
      root.classList.add("theme-fading");
      apply();
      window.setTimeout(() => root.classList.remove("theme-fading"), 420);
    }
  }, [theme]);

  return [theme, toggle];
}

export type TextSize = "normal" | "large" | "larger";
const SIZE_KEY = "nabz.textSize";
export const TEXT_SIZES: Record<TextSize, string> = { normal: "17px", large: "19px", larger: "21px" };

function savedSize(): TextSize {
  try {
    const s = localStorage.getItem(SIZE_KEY);
    return s === "large" || s === "larger" ? s : "normal";
  } catch {
    return "normal";
  }
}

/** Text size for the whole app (many users are older); every size in the design scales with the root size. */
export function useTextSize(): [TextSize, (s: TextSize) => void] {
  const [size, setSize] = useState<TextSize>(savedSize);
  useEffect(() => {
    document.documentElement.style.fontSize = TEXT_SIZES[size];
  }, [size]);
  const choose = useCallback((s: TextSize) => {
    setSize(s);
    try {
      localStorage.setItem(SIZE_KEY, s);
    } catch {
      /* storage unavailable: the choice lasts for this visit */
    }
  }, []);
  return [size, choose];
}
