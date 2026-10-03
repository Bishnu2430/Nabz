import { useState } from "react";
import { useTranslation } from "react-i18next";

import { useDecideLimit, useLimitsForReview, type LimitForReview } from "../../api/catalogue";
import { useToast } from "../../components/Toast";
import { Button, Card, Empty, ErrorNote, Loading, fieldClass } from "../../components/ui";
import { formatDate } from "../../lib/format";
import { LimitState } from "./CatalogueTab";

const side = (v: string | null) => v ?? "—";

/**
 * Critical limits decide when Nabz tells a family to contact a doctor today, so a change an administrator proposes
 * applies only when a clinical reviewer approves it here (docs/10 §4). Limits nobody has signed off yet follow.
 */
export function LimitsTab() {
  const { t } = useTranslation();
  const limits = useLimitsForReview();
  if (limits.isPending) return <Loading />;
  if (limits.isError) return <ErrorNote error={limits.error} />;
  if (limits.data.length === 0) return <Empty icon="shield">{t("limits.none")}</Empty>;
  return (
    <section>
      <p className="mb-4 max-w-prose text-muted">{t("limits.intro")}</p>
      <ul className="stagger space-y-3">
        {limits.data.map((l) => <li key={l.code}><LimitCard item={l} /></li>)}
      </ul>
    </section>
  );
}

function LimitCard({ item }: { item: LimitForReview }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const decide = useDecideLimit();
  const toast = useToast();
  const [note, setNote] = useState("");
  const { critical: c, unit } = item;
  const range = item.ranges.map((r) => `${side(r.low)} – ${side(r.high)}`).join("; ");
  const send = (approve: boolean) => decide.mutate({ code: item.code, approve, note }, {
    onSuccess: (r) => toast(approve
      ? t("limits.approved", { count: r.results_changed })
      : t("limits.rejected")),
  });

  return (
    <Card className="p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-display text-lg font-bold">{item.name}</h3>
        <LimitState limit={c} />
      </div>
      <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        <dt className="text-muted">{t("limits.current")}</dt>
        <dd className="tabular">{t("limits.below_above", { low: side(c.low), high: side(c.high), unit })}</dd>
        {c.proposed && (
          <>
            <dt className="text-muted">{t("limits.proposed")}</dt>
            <dd className="tabular font-medium text-borderline">
              {t("limits.below_above", { low: side(c.proposed.low), high: side(c.proposed.high), unit })}
            </dd>
            <dt className="text-muted">{t("limits.by")}</dt>
            <dd>{[c.proposed.by, formatDate(c.proposed.at, lang)].filter(Boolean).join(" · ")}{c.proposed.note && <> — “{c.proposed.note}”</>}</dd>
          </>
        )}
        {range && (<><dt className="text-muted">{t("limits.range")}</dt><dd className="tabular">{range} {unit}</dd></>)}
        <dt className="text-muted">{t("limits.source")}</dt><dd>{c.source}</dd>
      </dl>
      {decide.isError && <div className="mt-2"><ErrorNote error={decide.error} /></div>}
      {(c.proposed || !c.reviewed_at) && (
        <div className="mt-3 flex flex-wrap items-end gap-2">
          <label className="min-w-0 flex-1 text-sm">
            <span className="mb-1 block font-medium">{t("limits.note")}</span>
            <input value={note} maxLength={500} onChange={(e) => setNote(e.target.value)} className={fieldClass} />
          </label>
          <Button variant="primary" disabled={decide.isPending} onClick={() => send(true)}>
            {c.proposed ? t("limits.approve") : t("limits.sign_off")}
          </Button>
          {c.proposed && <Button disabled={decide.isPending} onClick={() => send(false)}>{t("limits.reject")}</Button>}
        </div>
      )}
    </Card>
  );
}
