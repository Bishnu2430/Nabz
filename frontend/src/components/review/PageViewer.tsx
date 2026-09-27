import clsx from "clsx";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import type { Observation, Page } from "../../api/types";

const PAD = 0.35; // % of page added around each box so the ink isn't clipped

/**
 * The report page as the person photographed or printed it, with a box over every value Nabz read.
 * Boxes are stored in page points, so they are drawn as percentages and line up at any zoom.
 */
export function PageViewer({ reportId, pages, rows, activeId, onSelect }: {
  reportId: string;
  pages: Page[];
  rows: Observation[];
  activeId: string | undefined;
  onSelect: (id: string) => void;
}) {
  const { t } = useTranslation();
  const [pageNo, setPageNo] = useState(pages[0]?.page_no ?? 0);
  const [zoomed, setZoomed] = useState(false);
  const activeBox = useRef<HTMLButtonElement>(null);
  const active = rows.find((r) => r.id === activeId);

  // Follow the selected row to its page, but only when the selection changes, so page tabs still work.
  const activePage = active?.bbox?.page;
  useEffect(() => {
    if (activePage !== undefined) setPageNo(activePage);
  }, [activeId, activePage]);

  // Bring the selected box into view inside the viewer only; scrolling the window would pull the list away.
  const scroller = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const box = activeBox.current;
    const sc = scroller.current;
    if (!box || !sc) return;
    const outside = (start: number, size: number, pos: number, view: number) => start < pos || start + size > pos + view;
    if (outside(box.offsetTop, box.offsetHeight, sc.scrollTop, sc.clientHeight)) {
      sc.scrollTo?.({ top: box.offsetTop - sc.clientHeight / 3, behavior: "smooth" });
    }
    if (outside(box.offsetLeft, box.offsetWidth, sc.scrollLeft, sc.clientWidth)) {
      sc.scrollTo?.({ left: box.offsetLeft - 16, behavior: "smooth" });
    }
  }, [activeId, pageNo, zoomed]);

  const page = pages.find((p) => p.page_no === pageNo);
  if (!page) return null;

  return (
    <figure className="overflow-hidden rounded-lg border border-hairline bg-sunken">
      <div className="flex items-center gap-2 border-b border-hairline bg-raised px-3 py-2 text-sm">
        {pages.length > 1 &&
          pages.map((p) => (
            <button
              key={p.page_no}
              type="button"
              onClick={() => setPageNo(p.page_no)}
              aria-pressed={p.page_no === pageNo}
              className={clsx("rounded px-2 py-0.5", p.page_no === pageNo ? "bg-sunken font-medium" : "text-muted")}
            >
              {t("review.page", { n: p.page_no + 1 })}
            </button>
          ))}
        <button type="button" onClick={() => setZoomed((z) => !z)} aria-pressed={zoomed} className="ml-auto rounded px-2 py-0.5 text-link">
          {zoomed ? t("review.zoom_out") : t("review.zoom_in")}
        </button>
      </div>
      <div ref={scroller} className="max-h-[45vh] overflow-auto lg:max-h-[75vh]">
        <div className={clsx("relative", zoomed ? "w-[200%]" : "w-full")}>
          <img
            src={`/v1/reports/${reportId}/pages/${pageNo}/image`}
            alt={t("review.page_alt", { n: pageNo + 1 })}
            className="block w-full select-none"
            draggable={false}
          />
          {rows
            .filter((r) => r.bbox && r.bbox.page === pageNo)
            .map((r) => {
              const b = r.bbox!;
              const isActive = r.id === activeId;
              return (
                <button
                  key={r.id}
                  ref={isActive ? activeBox : undefined}
                  type="button"
                  tabIndex={-1}
                  aria-hidden="true"
                  onClick={() => onSelect(r.id)}
                  style={{
                    left: `${(b.x0 / page.width) * 100 - PAD}%`,
                    top: `${(b.top / page.height) * 100 - PAD}%`,
                    width: `${((b.x1 - b.x0) / page.width) * 100 + 2 * PAD}%`,
                    height: `${((b.bottom - b.top) / page.height) * 100 + 2 * PAD}%`,
                  }}
                  className={clsx(
                    "absolute rounded-sm border transition",
                    isActive
                      ? "border-2 border-accent bg-accent/10"
                      : r.needs_attention
                        ? "border-borderline/80 bg-borderline/10 hover:bg-borderline/20"
                        : "border-transparent hover:border-ink/40",
                  )}
                />
              );
            })}
        </div>
      </div>
    </figure>
  );
}
