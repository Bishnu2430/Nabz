import clsx from "clsx";
import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";

/**
 * Small motion helpers. Everything here is decoration: content is in the page whether or not it animates, and the
 * global reduced-motion rule in index.css turns the movement off.
 */

/** Content that opens and closes smoothly (a grid row growing from 0 to its natural height). */
export function Collapse({ open, children, className }: { open: boolean; children: ReactNode; className?: string }) {
  return (
    <div className={clsx("grid transition-[grid-template-rows,opacity] duration-300 ease-out",
      open ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0", className)} aria-hidden={!open}>
      <div className="min-h-0 overflow-hidden" inert={!open}>{children}</div>
    </div>
  );
}

/**
 * Fades and lifts its content in when it scrolls into view, once. `delay` staggers siblings (ms).
 * Without IntersectionObserver (old browsers, tests) the content is simply shown.
 */
export function Reveal({ children, delay = 0, className, as: Tag = "div" }: {
  children: ReactNode;
  delay?: number;
  className?: string;
  as?: "div" | "li" | "section";
}) {
  const ref = useRef<HTMLElement>(null);
  const [shown, setShown] = useState(typeof IntersectionObserver === "undefined");
  useEffect(() => {
    const el = ref.current;
    if (!el || shown) return;
    const io = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) {
        setShown(true);
        io.disconnect();
      }
    }, { rootMargin: "0px 0px -8% 0px" });
    io.observe(el);
    return () => io.disconnect();
  }, [shown]);
  const style: CSSProperties = { transitionDelay: shown ? `${delay}ms` : undefined };
  return (
    // eslint-free project; the ref type is widened because Tag varies
    <Tag ref={ref as never} style={style} className={clsx("reveal", shown && "reveal-in", className)}>{children}</Tag>
  );
}

/** A number that counts up to its value when first shown (300–900 ms), then stays exact. */
export function CountUp({ value, decimals = 0, className }: { value: number; decimals?: number; className?: string }) {
  const [shown, setShown] = useState(value);
  const started = useRef(false);
  useEffect(() => {
    const reduce = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (started.current || reduce || typeof requestAnimationFrame === "undefined") {
      setShown(value);
      return;
    }
    started.current = true;
    const t0 = performance.now();
    const duration = 700;
    let frame = 0;
    const tick = (now: number) => {
      const k = Math.min(1, (now - t0) / duration);
      setShown(value * (1 - Math.pow(1 - k, 3)));
      if (k < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [value]);
  return <span className={className}>{shown.toFixed(decimals)}</span>;
}
