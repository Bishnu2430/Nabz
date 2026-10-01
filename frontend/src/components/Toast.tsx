import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";

interface Toast {
  id: number;
  text: string;
  tone: "ok" | "warn";
}

const ToastContext = createContext<(text: string, tone?: Toast["tone"]) => void>(() => {});

/** A short confirmation that something happened ("Note saved"), shown at the bottom for a few seconds. */
export function useToast() {
  return useContext(ToastContext);
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const next = useRef(1);
  const show = useCallback((text: string, tone: Toast["tone"] = "ok") => {
    const id = next.current++;
    setToasts((list) => [...list.slice(-2), { id, text, tone }]);
    window.setTimeout(() => setToasts((list) => list.filter((t) => t.id !== id)), 3200);
  }, []);
  const value = useMemo(() => show, [show]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div aria-live="polite" role="status"
        className="pointer-events-none fixed inset-x-0 bottom-5 z-[70] flex flex-col items-center gap-2 px-4 print:hidden">
        {toasts.map((t) => (
          <p key={t.id} className="toast pointer-events-auto flex items-center gap-2 rounded-full border border-hairline bg-raised px-4 py-2 text-sm shadow-lg">
            <span aria-hidden="true" className={t.tone === "ok" ? "text-normal" : "text-borderline"}>
              {t.tone === "ok" ? "✓" : "!"}
            </span>
            {t.text}
          </p>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
