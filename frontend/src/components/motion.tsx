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
  const [settled, setSettled] = useState(false);
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
  useEffect(() => {
    if (!shown || settled) return;
    const timer = window.setTimeout(() => setSettled(true), delay + 700);
    return () => window.clearTimeout(timer);
  }, [shown, settled, delay]);
  const style: CSSProperties = { transitionDelay: shown && !settled ? `${delay}ms` : undefined };
  return (
    // the ref type is widened because Tag varies
    <Tag ref={ref as never} style={style} className={clsx("reveal", shown && "reveal-in", className)}>{children}</Tag>
  );
}
