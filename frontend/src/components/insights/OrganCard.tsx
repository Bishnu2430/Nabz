import clsx from "clsx";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { Organ } from "../../api/types";
import { Icon, organIcon } from "../icons";
import { Button, Card } from "../ui";
import { ResultRow } from "./ResultRow";
import { STATUS_COLOR, StatusMark, isAbnormal } from "./StatusMark";

/** One organ system: its worst status, results out of range first, the rest folded away until asked for. */
export function OrganCard({ organ, profileId }: { organ: Organ; profileId: string }) {
  const { t, i18n } = useTranslation();
  const name = organ.names[i18n.resolvedLanguage ?? "en"] ?? organ.names.en;
  const flagged = organ.results.filter((r) => isAbnormal(r.status) || r.trend?.confirmed || r.change?.significant);
  const rest = organ.results.filter((r) => !flagged.includes(r));
  const [open, setOpen] = useState(flagged.length === 0 && rest.length <= 3);
  const shown = open ? [...flagged, ...rest] : flagged;

  return (
    <Card className="overflow-hidden">
      {/* the organ's colour runs down the edge like a brush stroke */}
      <div className="flex">
        <div aria-hidden="true" className="w-1.5 shrink-0" style={{ background: STATUS_COLOR[organ.status] }} />
        <div className="min-w-0 flex-1 p-5">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="flex items-center gap-2 font-display text-xl font-bold">
              <Icon name={organIcon(organ.code)} size={20} className="text-muted" />
              {name}
            </h2>
            <StatusMark status={organ.status} />
          </div>
          {shown.length > 0 && (
            <ul className={clsx("mt-2 divide-y divide-hairline")}>
              {shown.map((r) => <ResultRow key={r.observation_id} result={r} profileId={profileId} />)}
            </ul>
          )}
          {rest.length > 0 && (flagged.length > 0 || rest.length > 3) && (
            <Button variant="quiet" className="mt-1 px-0 text-sm" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
              {open ? t("insights.show_fewer") : t("insights.more_in_range", { count: rest.length })}
            </Button>
          )}
        </div>
      </div>
    </Card>
  );
}
