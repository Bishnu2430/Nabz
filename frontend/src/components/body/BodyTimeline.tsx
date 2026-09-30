import clsx from "clsx";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { useBodyMap } from "../../api/hooks";
import type { BodyMapFrame } from "../../api/types";
import { formatDate } from "../../lib/format";
import { STATUS_COLOR, StatusMark } from "../insights/StatusMark";
import { Button, Card } from "../ui";
import { BodyMap, useCountNote } from "./BodyMap";
import { isOrganCode, type OrganCode } from "./organs";

const STEP_MS = 1400;

/**
 * The body map across a person's reports (FR-29). The dates run along a handscroll; Play replays the body from
 * the first report to the latest.
 */
export function BodyTimeline({ profileId }: { profileId: string }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const frames = useBodyMap(profileId).data ?? [];
  const [index, setIndex] = useState<number | null>(null);
  const [organ, setOrgan] = useState<OrganCode | null>(null);
  const [playing, setPlaying] = useState(false);
  const scroller = useRef<HTMLOListElement>(null);
  const countNote = useCountNote();

  const current = index ?? frames.length - 1;
  const frame: BodyMapFrame | undefined = frames[current];

  useEffect(() => {
    if (!playing) return;
    if (current >= frames.length - 1) {
      setPlaying(false);
      return;
    }
    const timer = setTimeout(() => setIndex(current + 1), STEP_MS);
    return () => clearTimeout(timer);
  }, [playing, current, frames.length]);

  useEffect(() => {
    scroller.current?.querySelector<HTMLElement>(`[data-index="${current}"]`)
      ?.scrollIntoView?.({ inline: "center", block: "nearest", behavior: "smooth" });
  }, [current]);

  if (!frame) return null;
  const play = () => {
    if (current >= frames.length - 1) setIndex(0);
    setPlaying(true);
  };
  const chosen = frame.organs.find((o) => o.code === organ);

  return (
    <BodyMap
      items={frame.organs.filter((o) => isOrganCode(o.code)).map((o) => ({
        code: o.code as OrganCode,
        status: o.status,
        name: t(`organs.${o.code}`),
        note: countNote(o.out_of_range, o.results),
      }))}
      selected={organ}
      onSelect={setOrgan}
      detail={chosen && (
        <Card className="p-5">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h3 className="font-display text-xl font-bold">{t(`organs.${chosen.code}`)}</h3>
            <StatusMark status={chosen.status} />
          </div>
          <p className="mt-2 text-muted">
            {t("body.on_date", { date: formatDate(frame.date, lang) })} ·{" "}
            {countNote(chosen.out_of_range, chosen.results)}
          </p>
          <Link to={`/r/${frame.report_id}`} className="mt-3 inline-block text-link">{t("body.open_report")}</Link>
        </Card>
      )}
      footer={frames.length > 1 && (
        <div className="mt-4 flex items-center gap-3">
          <Button onClick={playing ? () => setPlaying(false) : play} aria-pressed={playing}>
            {playing ? t("body.pause") : t("body.play")}
          </Button>
          <ol ref={scroller} aria-label={t("body.timeline")}
            className="flex flex-1 gap-2 overflow-x-auto border-y border-hairline py-2 [scrollbar-width:thin]">
            {frames.map((f, i) => {
              const worst = f.organs[0]?.status ?? "unknown";
              return (
                <li key={f.report_id} data-index={i}>
                  <button type="button" aria-current={i === current ? "step" : undefined}
                    onClick={() => {
                      setPlaying(false);
                      setIndex(i);
                    }}
                    className={clsx("flex items-center gap-2 whitespace-nowrap rounded-full border px-3 py-1 text-sm",
                      i === current ? "border-ink bg-raised font-medium" : "border-hairline text-muted hover:border-ink/40")}>
                    <span aria-hidden="true" className="size-2 rounded-full" style={{ background: STATUS_COLOR[worst] }} />
                    {formatDate(f.date, lang)}
                  </button>
                </li>
              );
            })}
          </ol>
        </div>
      )}
    />
  );
}
