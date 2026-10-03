import { useEffect, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { useTranslation } from "react-i18next";

/** A dialog over the page: closes on Escape or a click outside, keeps the page from scrolling behind it. */
export function Modal({ title, onClose, children, wide = false }: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
}) {
  const { t } = useTranslation();
  const close = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    close.current?.focus();
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", key);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", key);
      document.body.style.overflow = overflow;
    };
  }, [onClose]);

  return createPortal(
    <div className="fade-in fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-black/50 p-4 backdrop-blur-sm"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}>
      <div role="dialog" aria-modal="true" aria-labelledby="modal-title"
        className={`pop card w-full rounded-lg border border-hairline bg-raised p-6 ${wide ? "max-w-2xl" : "max-w-lg"}`}
        style={{ transformOrigin: "center" }}>
        <div className="mb-4 flex items-start justify-between gap-4">
          <h2 id="modal-title" className="font-display text-2xl font-bold">{title}</h2>
          <button ref={close} type="button" onClick={onClose} aria-label={t("common.close")}
            className="btn grid size-9 shrink-0 place-items-center rounded-md border border-hairline hover:border-ink/40">✕</button>
        </div>
        {children}
      </div>
    </div>,
    document.body,
  );
}
