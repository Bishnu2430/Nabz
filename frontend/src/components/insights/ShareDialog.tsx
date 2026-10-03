import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "../../api/client";
import type { ShareCreated, ShareLink } from "../../api/types";
import { formatDate } from "../../lib/format";
import { Modal } from "../Modal";
import { useToast } from "../Toast";
import { Button, ErrorNote, fieldClass } from "../ui";

const DAYS = [1, 7, 30] as const;

/**
 * Share one report with a doctor (FR-34): a link that needs no account, shows only this report, stops working
 * after the chosen number of days, and can be withdrawn at any time. The link is shown once.
 */
export function ShareDialog({ reportId, onClose }: { reportId: string; onClose: () => void }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const qc = useQueryClient();
  const toast = useToast();
  const [days, setDays] = useState<(typeof DAYS)[number]>(7);
  const [label, setLabel] = useState("");
  const [made, setMade] = useState<ShareCreated | null>(null);
  const links = useQuery({ queryKey: ["shares", reportId], queryFn: () => api.get<ShareLink[]>(`/v1/reports/${reportId}/shares`) });
  const create = useMutation({
    mutationFn: () => api.post<ShareCreated>(`/v1/reports/${reportId}/shares`, { days, label: label.trim() || undefined }),
    onSuccess: (link) => {
      setMade(link);
      void qc.invalidateQueries({ queryKey: ["shares", reportId] });
    },
  });
  const revoke = useMutation({
    mutationFn: (id: string) => api.delete(`/v1/shares/${id}`),
    onSuccess: (_, id) => {
      if (made?.id === id) setMade(null);
      toast(t("share.withdrawn"));
      void qc.invalidateQueries({ queryKey: ["shares", reportId] });
    },
  });
  const copy = async (url: string) => {
    try {
      await navigator.clipboard.writeText(url);
      toast(t("share.copied"));
    } catch {
      /* clipboard unavailable: the link is on screen to select */
    }
  };

  return (
    <Modal title={t("share.title")} onClose={onClose} wide>
      <p className="text-muted">{t("share.intro")}</p>

      {made ? (
        <div className="rise mt-5 grid gap-5 sm:grid-cols-[auto_1fr] sm:items-center">
          <img src={made.qr_svg} alt={t("share.qr_alt")} className="mx-auto size-44 rounded-md border border-hairline" />
          <div className="min-w-0">
            <p className="font-medium">{t("share.ready")}</p>
            <p className="mt-1 text-sm text-muted">{t("share.expires", { date: formatDate(made.expires_at, lang) })}</p>
            <input readOnly value={made.url} onFocus={(e) => e.currentTarget.select()} aria-label={t("share.link")}
              className={`${fieldClass} mt-3 font-mono text-sm`} />
            <div className="mt-3 flex flex-wrap gap-2">
              <Button variant="primary" onClick={() => void copy(made.url)}>{t("share.copy")}</Button>
              <a href={made.url} target="_blank" rel="noreferrer"
                className="btn rounded-md border border-hairline bg-raised px-4 py-2 font-medium no-underline hover:border-ink/40">
                {t("share.preview")} ↗
              </a>
            </div>
            <p className="mt-3 text-sm text-muted">{t("share.once")}</p>
          </div>
        </div>
      ) : (
        <form className="mt-5 grid gap-4 sm:grid-cols-2" onSubmit={(e) => { e.preventDefault(); create.mutate(); }}>
          <label>
            <span className="mb-1 block font-medium">{t("share.for")}</span>
            <input value={label} maxLength={80} onChange={(e) => setLabel(e.target.value)} className={fieldClass}
              placeholder={t("share.for_placeholder")} />
          </label>
          <label>
            <span className="mb-1 block font-medium">{t("share.works_for")}</span>
            <select value={days} onChange={(e) => setDays(Number(e.target.value) as (typeof DAYS)[number])} className={fieldClass}>
              {DAYS.map((d) => <option key={d} value={d}>{t("share.days", { count: d })}</option>)}
            </select>
          </label>
          {create.isError && <div className="sm:col-span-2"><ErrorNote error={create.error} /></div>}
          <div className="sm:col-span-2">
            <Button type="submit" variant="primary" disabled={create.isPending}>{t("share.create")}</Button>
          </div>
        </form>
      )}

      {(links.data?.length ?? 0) > 0 && (
        <section className="mt-6 border-t border-hairline pt-4" aria-labelledby="share-links-h">
          <h3 id="share-links-h" className="mb-2 font-medium">{t("share.links")}</h3>
          <ul className="divide-y divide-hairline">
            {links.data!.map((l) => (
              <li key={l.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 py-2 text-sm">
                <span className="font-medium">{l.label ?? t("share.unnamed")}</span>
                <span className={l.active ? "text-normal" : "text-muted"}>
                  {l.active ? t("share.expires", { date: formatDate(l.expires_at, lang) })
                    : l.revoked ? t("share.state_withdrawn") : t("share.state_expired")}
                </span>
                <span className="text-muted">{t("share.opened", { count: l.views })}</span>
                {l.active && (
                  <button type="button" disabled={revoke.isPending} onClick={() => revoke.mutate(l.id)}
                    className="ml-auto text-abnormal hover:underline">
                    {t("share.withdraw")}
                  </button>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}
    </Modal>
  );
}
