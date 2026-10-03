import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { useRegistration, useSaveRegistration, useSharedWithMe, type Registration } from "../../api/clinicians";
import { Icon } from "../../components/icons";
import { useToast } from "../../components/Toast";
import { Button, Card, Empty, ErrorNote, Field, Loading, PageTitle, PersonSeal, SectionTitle } from "../../components/ui";
import { formatDate } from "../../lib/format";

/**
 * A doctor's home on Nabz (docs/12 §2): their medical-council registration and whether an admin has checked it, and,
 * once it has, the reports families have shared with them.
 */
export default function ClinicianHome() {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const registration = useRegistration();
  const [editing, setEditing] = useState(false);
  if (registration.isPending) return <Loading />;
  if (registration.isError) return <ErrorNote error={registration.error} onRetry={() => void registration.refetch()} />;
  const reg = registration.data;
  const verified = Boolean(reg?.verified_at);

  return (
    <>
      <PageTitle icon="stethoscope" title={t("clinician.title")} subtitle={t("clinician.intro")} />
      <div className="grid gap-8 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
        <section aria-labelledby="cl-shared-h">
          <SectionTitle id="cl-shared-h" icon="share" title={t("clinician.shared")} />
          {verified ? <SharedList /> : (
            <Empty icon="shield">{reg ? t("clinician.waiting") : t("clinician.register_first")}</Empty>
          )}
        </section>
        <section aria-labelledby="cl-reg-h">
          <SectionTitle id="cl-reg-h" icon="key" title={t("clinician.registration")}
            action={reg && !editing && <Button variant="quiet" onClick={() => setEditing(true)}>{t("clinician.edit")}</Button>} />
          {!reg || editing ? (
            <Card className="p-5"><RegistrationForm current={reg} onDone={() => setEditing(false)} /></Card>
          ) : (
            <Card className="p-5">
              <p className="font-display text-xl font-bold">{reg.full_name}</p>
              <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
                <dt className="text-muted">{t("clinician.f_registration_no")}</dt><dd className="tabular">{reg.registration_no}</dd>
                <dt className="text-muted">{t("clinician.f_council")}</dt><dd>{reg.council}</dd>
                {reg.specialty && <><dt className="text-muted">{t("clinician.f_specialty")}</dt><dd>{reg.specialty}</dd></>}
              </dl>
              <p className={`mt-4 flex items-center gap-2 text-sm ${verified ? "text-normal" : "text-borderline"}`}>
                <Icon name={verified ? "check" : "clock"} size={16} />
                {verified ? t("clinician.verified", { date: formatDate(reg.verified_at, lang) }) : t("clinician.unverified")}
              </p>
            </Card>
          )}
          <p className="mt-3 max-w-prose text-sm text-muted">{t("clinician.verify_note")}</p>
        </section>
      </div>
    </>
  );
}

function SharedList() {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const shared = useSharedWithMe();
  if (shared.isPending) return <Loading />;
  if (shared.isError) return <ErrorNote error={shared.error} />;
  if (shared.data.length === 0) return <Empty icon="share">{t("clinician.none_shared")}</Empty>;
  return (
    <ul className="stagger space-y-3">
      {shared.data.map((s) => (
        <li key={s.report_id}>
          <Link to={`/clinician/r/${s.report_id}`} className="block no-underline">
            <Card className="flex items-center gap-4 px-4 py-3 transition-colors hover:border-ink/40">
              <PersonSeal name={s.person.display_name} />
              <div className="min-w-0 flex-1">
                <p className="font-medium">{s.person.display_name}</p>
                <p className="text-sm text-muted">
                  {[s.person.age != null && t("summary.age", { count: s.person.age }), t(`profile_form.sex_${s.person.sex}`),
                    s.lab_name, s.collected_at && formatDate(s.collected_at, lang)].filter(Boolean).join(" · ")}
                </p>
              </div>
              <div className="text-right text-sm text-muted">
                <p>{t("clinician.shared_on", { date: formatDate(s.shared_at, lang) })}</p>
                {s.notes > 0 && <p className="text-normal">{t("clinician.notes_count", { count: s.notes })}</p>}
              </div>
            </Card>
          </Link>
        </li>
      ))}
    </ul>
  );
}

const FIELDS = { full_name: 120, registration_no: 40, council: 120, specialty: 80 } as const;

function RegistrationForm({ current, onDone }: { current: Registration | null; onDone: () => void }) {
  const { t } = useTranslation();
  const toast = useToast();
  const save = useSaveRegistration();
  const [form, setForm] = useState({
    full_name: current?.full_name ?? "", registration_no: current?.registration_no ?? "",
    council: current?.council ?? "", specialty: current?.specialty ?? "",
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate({ ...form, specialty: form.specialty.trim() || null }, {
      onSuccess: () => { toast(t("clinician.saved")); onDone(); },
    });
  };
  return (
    <form onSubmit={submit} className="space-y-4">
      {(Object.keys(FIELDS) as (keyof typeof FIELDS)[]).map((f) => (
        <Field key={f} id={`cl-${f}`} label={t(`clinician.f_${f}`)} value={form[f]} required={f !== "specialty"}
          minLength={f === "specialty" ? undefined : 2} maxLength={FIELDS[f]} hint={f === "council" ? t("clinician.council_hint") : undefined}
          onChange={(e) => setForm({ ...form, [f]: e.target.value })} />
      ))}
      {current?.verified_at && <p className="text-sm text-muted">{t("clinician.reverify")}</p>}
      {save.isError && <ErrorNote error={save.error} />}
      <div className="flex gap-2">
        <Button type="submit" variant="primary" disabled={save.isPending}>{t(current ? "clinician.save" : "clinician.register")}</Button>
        {current && <Button type="button" onClick={onDone}>{t("common.cancel")}</Button>}
      </div>
    </form>
  );
}
