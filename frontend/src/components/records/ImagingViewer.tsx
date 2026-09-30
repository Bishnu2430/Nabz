import clsx from "clsx";
import { useCallback, useEffect, useRef, useState, type PointerEvent, type ReactNode, type WheelEvent } from "react";
import { useTranslation } from "react-i18next";

import { recordFileUrl, recordImageUrl } from "../../api/hooks";
import type { HealthRecord } from "../../api/types";
import { formatDate } from "../../lib/format";

type Tool = "move" | "adjust" | "loupe";
const MIN_ZOOM = 0.5;
const MAX_ZOOM = 8;
const LOUPE = 180; // px, diameter
const LOUPE_ZOOM = 2.5;

interface View {
  scale: number;
  x: number; // offset of the image centre from the viewport centre, px
  y: number;
  rotation: number; // degrees, multiples of 90
  brightness: number; // 1 = as taken
  contrast: number;
  invert: boolean;
}

const START: View = { scale: 1, x: 0, y: 0, rotation: 0, brightness: 1, contrast: 1, invert: false };
const clamp = (v: number, lo: number, hi: number) => Math.min(Math.max(v, lo), hi);

/**
 * A study viewer for X-rays and scans: zoom (wheel, pinch, buttons), pan, brightness and contrast (sliders, or
 * drag like a radiologist's window/level), invert, rotate, a magnifying loupe and full screen, beside the report's
 * own findings and impression. Nabz shows the images; it does not read or interpret them.
 */
export function ImagingViewer({ record, onClose }: { record: HealthRecord; onClose: () => void }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const [view, setView] = useState<View>(START);
  const [tool, setTool] = useState<Tool>("move");
  const [loupe, setLoupe] = useState<{ x: number; y: number } | null>(null);
  const [fit, setFit] = useState<{ w: number; h: number } | null>(null);
  const root = useRef<HTMLDivElement>(null);
  const stage = useRef<HTMLDivElement>(null);
  const pointers = useRef(new Map<number, { x: number; y: number }>());
  const drag = useRef<{ x: number; y: number; view: View; pinch?: number } | null>(null);
  const close = useRef<HTMLButtonElement>(null);
  const src = recordImageUrl(record.id);

  const zoomAt = useCallback((factor: number, px = 0, py = 0) => {
    setView((v) => {
      const scale = clamp(v.scale * factor, MIN_ZOOM, MAX_ZOOM);
      const k = scale / v.scale;
      // keep the point under the cursor where it is
      return { ...v, scale, x: px - (px - v.x) * k, y: py - (py - v.y) * k };
    });
  }, []);

  // keyboard: + − 0 r i, arrows to pan, Esc to close
  useEffect(() => {
    close.current?.focus();
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      else if (e.key === "+" || e.key === "=") zoomAt(1.25);
      else if (e.key === "-") zoomAt(0.8);
      else if (e.key === "0") setView(START);
      else if (e.key === "r") setView((v) => ({ ...v, rotation: (v.rotation + 90) % 360 }));
      else if (e.key === "i") setView((v) => ({ ...v, invert: !v.invert }));
      else if (e.key.startsWith("Arrow")) {
        const d = 40;
        setView((v) => ({ ...v, x: v.x + (e.key === "ArrowLeft" ? d : e.key === "ArrowRight" ? -d : 0),
          y: v.y + (e.key === "ArrowUp" ? d : e.key === "ArrowDown" ? -d : 0) }));
      } else return;
      e.preventDefault();
    };
    document.addEventListener("keydown", key);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", key);
      document.body.style.overflow = overflow;
    };
  }, [onClose, zoomAt]);

  const local = (e: { clientX: number; clientY: number }) => {
    const r = stage.current!.getBoundingClientRect();
    return { x: e.clientX - r.left - r.width / 2, y: e.clientY - r.top - r.height / 2, left: e.clientX - r.left,
      top: e.clientY - r.top };
  };

  const onWheel = (e: WheelEvent) => {
    const p = local(e);
    zoomAt(Math.exp(-e.deltaY * 0.0015), p.x, p.y);
  };

  const onPointerDown = (e: PointerEvent) => {
    stage.current?.setPointerCapture(e.pointerId);
    pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    const pts = [...pointers.current.values()];
    drag.current = { x: e.clientX, y: e.clientY, view,
      pinch: pts.length === 2 ? Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y) : undefined };
  };

  const onPointerMove = (e: PointerEvent) => {
    const p = local(e);
    if (tool === "loupe") setLoupe({ x: p.left, y: p.top });
    if (!pointers.current.has(e.pointerId) || !drag.current) return;
    pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    const start = drag.current;
    const pts = [...pointers.current.values()];
    if (pts.length === 2 && start.pinch) {
      const d = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
      setView({ ...start.view, scale: clamp(start.view.scale * (d / start.pinch), MIN_ZOOM, MAX_ZOOM) });
      return;
    }
    const dx = e.clientX - start.x;
    const dy = e.clientY - start.y;
    if (tool === "adjust") {
      // window/level: across for contrast, down for brightness
      setView({ ...start.view, contrast: clamp(start.view.contrast + dx / 300, 0.3, 3),
        brightness: clamp(start.view.brightness - dy / 300, 0.3, 2.5) });
    } else if (tool === "move") {
      setView({ ...start.view, x: start.view.x + dx, y: start.view.y + dy });
    }
  };

  const onPointerUp = (e: PointerEvent) => {
    pointers.current.delete(e.pointerId);
    drag.current = pointers.current.size ? { ...drag.current!, view } : null;
  };

  const fullScreen = () => {
    if (document.fullscreenElement) void document.exitFullscreen();
    else void root.current?.requestFullscreen?.();
  };

  const filter = `brightness(${view.brightness}) contrast(${view.contrast})${view.invert ? " invert(1)" : ""}`;
  const transform = (scale: number, x: number, y: number) =>
    `translate(-50%, -50%) translate(${x}px, ${y}px) scale(${scale}) rotate(${view.rotation}deg)`;
  const imageStyle = (w?: number, h?: number) => ({
    width: w, height: h, left: "50%", top: "50%", filter, position: "absolute" as const, maxWidth: "none",
  });
  const title = record.study_title ?? record.title;
  const date = [record.record_date && formatDate(record.record_date, lang), record.facility].filter(Boolean).join(" · ");

  return (
    <div ref={root} role="dialog" aria-modal="true" aria-labelledby="viewer-title"
      className="fixed inset-0 z-50 flex flex-col bg-[#0f0c0a] text-[#ede3d1] lg:flex-row">
      <div className="relative min-h-[55vh] flex-1 overflow-hidden lg:min-h-0">
        <div ref={stage} role="img" aria-label={t("viewer.image_label", { title })}
          className={clsx("absolute inset-0 touch-none select-none",
            tool === "move" ? "cursor-grab active:cursor-grabbing" : tool === "adjust" ? "cursor-crosshair" : "cursor-none")}
          onWheel={onWheel} onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp} onPointerLeave={() => setLoupe(null)}
          onDoubleClick={(e) => {
            const p = local(e);
            if (view.scale > 1.05) setView((v) => ({ ...v, scale: 1, x: 0, y: 0 }));
            else zoomAt(2.5, p.x, p.y);
          }}>
          <img src={src} alt="" draggable={false}
            onLoad={(e) => {
              // fit the whole study in the stage at 100 %
              const img = e.currentTarget;
              const r = stage.current!.getBoundingClientRect();
              const k = Math.min((r.width - 48) / img.naturalWidth, (r.height - 48) / img.naturalHeight);
              setFit({ w: img.naturalWidth * k, h: img.naturalHeight * k });
            }}
            style={{ ...imageStyle(fit?.w, fit?.h), transform: transform(view.scale, view.x, view.y),
              visibility: fit ? "visible" : "hidden" }} />
          {tool === "loupe" && loupe && fit && (
            <div aria-hidden="true" className="pointer-events-none absolute overflow-hidden rounded-full border-2 border-[#c9a55a] shadow-2xl"
              style={{ width: LOUPE, height: LOUPE, left: loupe.x - LOUPE / 2, top: loupe.y - LOUPE / 2 }}>
              <div className="absolute" style={{ width: stage.current?.clientWidth, height: stage.current?.clientHeight,
                left: LOUPE / 2 - loupe.x, top: LOUPE / 2 - loupe.y }}>
                <img src={src} alt="" draggable={false} style={{ ...imageStyle(fit.w, fit.h),
                  transform: (() => {
                    // the point under the pointer stays at the loupe's centre, magnified
                    const px = loupe.x - (stage.current?.clientWidth ?? 0) / 2;
                    const py = loupe.y - (stage.current?.clientHeight ?? 0) / 2;
                    return transform(view.scale * LOUPE_ZOOM, px - LOUPE_ZOOM * (px - view.x), py - LOUPE_ZOOM * (py - view.y));
                  })() }} />
              </div>
            </div>
          )}
        </div>
        <p className="pointer-events-none absolute bottom-2 left-3 right-3 text-center text-xs text-[#a89a82]">
          {record.image_credit}
        </p>
        <p className="pointer-events-none absolute left-3 top-3 rounded bg-black/50 px-2 py-1 text-xs tabular-nums">
          {Math.round(view.scale * 100)} % · {t("viewer.brightness_short", { v: Math.round(view.brightness * 100) })} ·{" "}
          {t("viewer.contrast_short", { v: Math.round(view.contrast * 100) })}
          {view.invert && ` · ${t("viewer.inverted")}`}
        </p>
      </div>

      <aside className="flex max-h-[45vh] w-full shrink-0 flex-col overflow-y-auto border-t border-[#3a3029] bg-[#16120f] p-5 lg:max-h-none lg:w-96 lg:border-l lg:border-t-0">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-sm text-[#a89a82]">{t(`records.kind_${record.kind}`)}</p>
            <h2 id="viewer-title" className="font-display text-2xl font-bold">{title}</h2>
            {date && <p className="text-sm text-[#a89a82]">{date}</p>}
          </div>
          <button ref={close} type="button" onClick={onClose} aria-label={t("viewer.close")}
            className="grid size-9 shrink-0 place-items-center rounded-md border border-[#3a3029] hover:border-[#c9a55a]">✕</button>
        </div>

        <div className="mt-4" role="toolbar" aria-label={t("viewer.tools")}>
          <div className="grid grid-cols-3 gap-1 rounded-md border border-[#3a3029] p-1">
            {(["move", "adjust", "loupe"] as Tool[]).map((k) => (
              <button key={k} type="button" aria-pressed={tool === k} onClick={() => setTool(k)}
                className={clsx("rounded px-2 py-1.5 text-sm", tool === k ? "bg-[#c9a55a] text-[#16120f]" : "hover:bg-[#211b16]")}>
                {t(`viewer.tool_${k}`)}
              </button>
            ))}
          </div>
          <p className="mt-1 text-xs text-[#a89a82]">{t(`viewer.hint_${tool}`)}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Tb onClick={() => zoomAt(0.8)} label={t("viewer.zoom_out")}>−</Tb>
            <Tb onClick={() => zoomAt(1.25)} label={t("viewer.zoom_in")}>+</Tb>
            <Tb onClick={() => setView((v) => ({ ...v, scale: 1, x: 0, y: 0 }))} label={t("viewer.fit")}>{t("viewer.fit")}</Tb>
            <Tb onClick={() => setView((v) => ({ ...v, rotation: (v.rotation + 90) % 360 }))} label={t("viewer.rotate")}>⟳</Tb>
            <Tb onClick={() => setView((v) => ({ ...v, invert: !v.invert }))} label={t("viewer.invert")}
              pressed={view.invert}>{t("viewer.invert")}</Tb>
            <Tb onClick={fullScreen} label={t("viewer.full_screen")}>⛶</Tb>
            <Tb onClick={() => setView(START)} label={t("viewer.reset")}>{t("viewer.reset")}</Tb>
          </div>
          <Slider label={t("viewer.brightness")} value={view.brightness} min={0.3} max={2.5}
            onChange={(v) => setView((s) => ({ ...s, brightness: v }))} />
          <Slider label={t("viewer.contrast")} value={view.contrast} min={0.3} max={3}
            onChange={(v) => setView((s) => ({ ...s, contrast: v }))} />
          <p className="mt-2 text-xs text-[#a89a82]">{t("viewer.keys")}</p>
        </div>

        {(record.findings?.length ?? 0) > 0 && (
          <section className="mt-5" aria-labelledby="viewer-findings">
            <h3 id="viewer-findings" className="text-sm font-semibold uppercase tracking-wide text-[#c9a55a]">{t("viewer.findings")}</h3>
            <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">{record.findings!.map((f) => <li key={f}>{f}</li>)}</ul>
          </section>
        )}
        {(record.impression?.length ?? 0) > 0 && (
          <section className="mt-4" aria-labelledby="viewer-impression">
            <h3 id="viewer-impression" className="text-sm font-semibold uppercase tracking-wide text-[#c9a55a]">{t("viewer.impression")}</h3>
            <ul className="mt-1 space-y-1 text-sm font-medium">{record.impression!.map((f) => <li key={f}>{f}</li>)}</ul>
          </section>
        )}
        {record.notes && <p className="mt-4 text-sm"><span className="text-[#a89a82]">{t("records.notes")}:</span> {record.notes}</p>}
        <p className="mt-4 text-xs text-[#a89a82]">{t("viewer.not_read")}</p>
        <a href={recordFileUrl(record.id)} target="_blank" rel="noreferrer" className="mt-3 text-sm text-[#8fa9c4]">
          {t("viewer.full_report")} →
        </a>
      </aside>
    </div>
  );
}

function Tb({ onClick, label, pressed, children }: { onClick: () => void; label: string; pressed?: boolean; children: ReactNode }) {
  return (
    <button type="button" onClick={onClick} aria-label={label} title={label} aria-pressed={pressed}
      className={clsx("min-w-9 rounded-md border px-2.5 py-1 text-sm",
        pressed ? "border-[#c9a55a] bg-[#c9a55a] text-[#16120f]" : "border-[#3a3029] hover:border-[#c9a55a]")}>
      {children}
    </button>
  );
}

function Slider({ label, value, min, max, onChange }: {
  label: string;
  value: number;
  min: number;
  max: number;
  onChange: (v: number) => void;
}) {
  return (
    <label className="mt-3 block text-sm">
      <span className="flex justify-between"><span>{label}</span><span className="tabular-nums text-[#a89a82]">{Math.round(value * 100)} %</span></span>
      <input type="range" min={min} max={max} step={0.01} value={value} onChange={(e) => onChange(Number(e.target.value))}
        className="mt-1 w-full accent-[#c9a55a]" />
    </label>
  );
}
