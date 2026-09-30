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

/** Sumi-e (light) or urushi (dark). Follows the system until the user picks one. */
export function useTheme(): [Theme, () => void] {
  const [theme, setTheme] = useState<Theme>(() => savedTheme() ?? systemTheme());

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const toggle = useCallback(() => {
    setTheme((t) => {
      const next = t === "light" ? "dark" : "light";
      try {
        localStorage.setItem(KEY, next);
      } catch {
        /* storage unavailable: the choice lasts for this visit */
      }
      return next;
    });
  }, []);

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
