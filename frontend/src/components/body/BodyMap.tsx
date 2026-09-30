import clsx from "clsx";
import { Component, lazy, Suspense, useEffect, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import type { ObsStatus } from "../../api/types";
import { STATUS_COLOR, StatusIcon } from "../insights/StatusMark";
import { BodyDiagram } from "./BodyDiagram";
import type { OrganCode, OrganStatus } from "./organs";

const Body3D = lazy(() => import("./Body3D"));

export interface BodyMapItem {
  code: OrganCode;
  status: ObsStatus;
  name: string;
  /** The worst result exactly, e.g. "Creatinine 1.85 mg/dL, 42 % above the upper limit 1.30". */
  note?: string;
}

type View = "3d" | "2d";
const VIEW_KEY = "nabz.bodyView";

export function hasWebGL2(): boolean {
  try {
    return Boolean(document.createElement("canvas").getContext("webgl2"));
  } catch {
    return false;
  }
}

function useReducedMotion(): boolean {
  const query = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)");
  const [reduced, setReduced] = useState(Boolean(query && query.matches));
  useEffect(() => {
    if (!query) return;
    const change = () => setReduced(query.matches);
    query.addEventListener("change", change);
    return () => query.removeEventListener("change", change);
  }, [query]);
  return reduced;
}

/** 3D where WebGL 2 works and the person hasn't chosen the flat map; the flat map otherwise (FR-31). */
function useView(): { view: View; setView: (v: View) => void; can3d: boolean } {
  const [can3d] = useState(hasWebGL2);
  const [chosen, setChosen] = useState<View | null>(() => {
    try {
      const v = localStorage.getItem(VIEW_KEY);
      return v === "3d" || v === "2d" ? v : null;
    } catch {
      return null;
    }
  });
  const setView = (v: View) => {
    setChosen(v);
    try {
      localStorage.setItem(VIEW_KEY, v);
    } catch {
      /* the choice lasts for this visit */
    }
  };
  return { view: can3d ? (chosen ?? "3d") : "2d", setView, can3d };
}

/** If the GPU refuses a WebGL context after all, show the flat map rather than a broken page. */
class WebGLBoundary extends Component<{ fallback: ReactNode; children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}

/**
 * The body map (FR-27, FR-28, FR-31): the body, the list of organ systems as buttons (the keyboard and
 * screen-reader way in), and the chosen system's card.
 */
export function BodyMap({ items, selected, onSelect, detail, footer }: {
  items: BodyMapItem[];
  selected: OrganCode | null;
  onSelect: (code: OrganCode | null) => void;
  detail?: ReactNode;
  footer?: ReactNode;
}) {
  const { t } = useTranslation();
  const { view, setView, can3d } = useView();
  const reduced = useReducedMotion();
  const statuses: OrganStatus = Object.fromEntries(items.map((i) => [i.code, i.status]));
  const labels = Object.fromEntries(items.map((i) => [i.code, `${i.name}: ${t(`result_status.${i.status}`)}`]));
  const toggle = (code: OrganCode) => onSelect(selected === code ? null : code);

  const flat = (
    <BodyDiagram statuses={statuses} selected={selected} onSelect={toggle} labels={labels}
      className="mx-auto h-full max-h-full w-auto py-4" />
  );
  const summary = items.map((i) => labels[i.code]).join("; ");

  return (
    <section aria-labelledby="body-h" className="mb-10">
      <h2 id="body-h" className="sr-only">{t("body.title")}</h2>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,4fr)]">
        <div className={clsx("relative overflow-hidden rounded-lg border border-hairline",
          view === "3d" ? "lacquer-stage" : "bg-sunken")}>
          <div className="h-[420px] sm:h-[520px]">
            {view === "3d" ? (
              <div role="img" aria-label={t("body.label_3d", { summary })} className="size-full">
                <WebGLBoundary fallback={flat}>
                  <Suspense fallback={<p className="grid size-full place-items-center text-sm text-[#a89a82]">{t("common.loading")}</p>}>
                    <Body3D statuses={statuses} selected={selected} onSelect={toggle} reducedMotion={reduced}
                      names={Object.fromEntries(items.map((i) => [i.code, i.name]))} />
                  </Suspense>
                </WebGLBoundary>
              </div>
            ) : flat}
          </div>
          <div className="absolute right-3 top-3 flex gap-2">
            {selected && (
              <StageButton onClick={() => onSelect(null)} dark={view === "3d"}>{t("body.whole")}</StageButton>
            )}
            {can3d && (
              <StageButton onClick={() => setView(view === "3d" ? "2d" : "3d")} dark={view === "3d"}>
                {view === "3d" ? t("body.view_2d") : t("body.view_3d")}
              </StageButton>
            )}
          </div>
          <p className={clsx("absolute bottom-3 left-3 right-3 text-center text-sm",
            view === "3d" ? "text-[#a89a82]" : "text-muted")}>
            {can3d ? (view === "3d" ? t("body.hint_3d") : t("body.hint_2d")) : t("body.no_webgl")}
          </p>
        </div>

        <div>
          {/* the chosen system's panel replaces the list; its back button returns to it */}
          {selected && detail ? detail : (
          <ul className="grid gap-2" aria-label={t("body.systems")}>
            {items.map((i) => (
              <li key={i.code}>
                <button type="button" aria-pressed={selected === i.code} onClick={() => toggle(i.code)}
                  className={clsx("flex w-full items-center gap-3 overflow-hidden rounded-md border bg-raised text-left transition",
                    selected === i.code ? "border-ink/60" : "border-hairline hover:border-ink/40")}>
                  <span aria-hidden="true" className="w-1.5 self-stretch" style={{ background: STATUS_COLOR[i.status] }} />
                  <span className="min-w-0 flex-1 py-2.5">
                    <span className="block font-medium">{i.name}</span>
                    {i.note && <span className="tabular block text-sm text-muted">{i.note}</span>}
                  </span>
                  <span className={clsx("flex shrink-0 items-center gap-1 pr-3 text-sm",
                    i.status === "normal" ? "text-normal" : i.status === "unknown" ? "text-muted" : "text-abnormal")}>
                    <StatusIcon status={i.status} />
                    {t(`result_status.${i.status}`)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
          )}
        </div>
      </div>
      {footer}
    </section>
  );
}

function StageButton({ onClick, dark, children }: { onClick: () => void; dark: boolean; children: ReactNode }) {
  return (
    <button type="button" onClick={onClick} className={clsx("rounded-md border px-3 py-1.5 text-sm backdrop-blur",
      dark ? "border-[#3a3029] bg-[#211b16]/80 text-[#ede3d1] hover:border-[#c9a55a]"
        : "border-hairline bg-raised/80 hover:border-ink/40")}>
      {children}
    </button>
  );
}
