import { useState } from "react";
import { useTranslation } from "react-i18next";

import { useDoctorNotes, useGrant, useGrants, useWithdrawGrant } from "../../api/clinicians";
import { formatDate } from "../../lib/format";
import { Icon } from "../icons";
import { useToast } from "../Toast";
import { Button, Card, ErrorNote, SectionTitle, fieldClass } from "../ui";

/**
 * Share a report with a doctor who has a verified account on Nabz (docs/12 §2): they see it, read-only, under
 * "Shared with me" until the family withdraws it, and can leave a note the family sees beside the report.
 */
export function DoctorShare({ reportId }: { reportId: string }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const toast = useToast();
  const [email, setEmail] = useState("");
  const grants = useGrants(reportId);
  const grant = useGrant(reportId);
  const withdraw = useWithdrawGrant(reportId);
  const active = grants.data?.filter((g) => !g.revoked) ?? [];

  return (
    <section className="mt-6 border-t border-hairline pt-4" aria-labelledby="share-doctor-h">
      <h3 id="share-doctor-h" className="flex items-center gap-2 font-medium">
        <Icon name="stethoscope" size={18} className="text-muted" />{t("share.doctor_title")}
      </h3>
      <p className="mt-1 text-sm text-muted">{t("share.doctor_intro")}</p>
      <form className="mt-3 flex flex-wrap items-end gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          grant.mutate(email.trim(), { onSuccess: (g) => { setEmail(""); toast(t("share.doctor_shared", { name: g.clinician_name })); } });
        }}>
        <label className="min-w-0 flex-1">
          <span className="mb-1 block text-sm font-medium">{t("share.doctor_email")}</span>
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className={fieldClass}
            autoComplete="off" placeholder={t("share.doctor_email_placeholder")} />
        </label>
        <Button type="submit" variant="primary" disabled={grant.isPending || !email.trim()}>{t("share.doctor_share")}</Button>
      </form>
      {grant.isError && <div className="mt-2"><ErrorNote error={grant.error} /></div>}
      {active.length > 0 && (
        <ul className="mt-3 divide-y divide-hairline">
          {active.map((g) => (
            <li key={g.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 py-2 text-sm">
              <span>
                <span className="font-medium">{g.clinician_name}</span>
                <span className="text-muted"> · {[g.specialty, `${g.council} ${g.registration_no}`].filter(Boolean).join(" · ")}</span>
              </span>
              <span className="text-muted">{t("share.doctor_since", { date: formatDate(g.created_at, lang) })}</span>
              {g.notes > 0 && <span className="text-normal">{t("share.doctor_notes", { count: g.notes })}</span>}
              <button type="button" disabled={withdraw.isPending} className="ml-auto text-abnormal hover:underline"
                onClick={() => withdraw.mutate(g.id, { onSuccess: () => toast(t("share.doctor_withdrawn")) })}>
                {t("share.withdraw")}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/** Notes from the doctors a report was shared with, beside the report. Nothing is shown when there are none. */
export function DoctorNotes({ reportId }: { reportId: string }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const notes = useDoctorNotes(reportId);
  if (!notes.data?.length) return null;
  return (
    <section className="mb-6" aria-labelledby="doctor-notes-h">
      <SectionTitle id="doctor-notes-h" icon="stethoscope" title={t("insights.doctor_notes", { count: notes.data.length })} />
      <Card className="divide-y divide-hairline">
        {notes.data.map((n) => (
          <figure key={n.id} className="px-4 py-3">
            <blockquote className="whitespace-pre-line">{n.text}</blockquote>
            <figcaption className="mt-1 text-sm text-muted">
              {[n.clinician_name ?? t("insights.doctor_removed"), formatDate(n.created_at, lang)].join(" · ")}
            </figcaption>
          </figure>
        ))}
      </Card>
    </section>
  );
}
