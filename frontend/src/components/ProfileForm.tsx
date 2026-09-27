import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { useCreateProfile } from "../api/hooks";
import type { Lang, Profile, Relationship, Sex } from "../api/types";
import { LANGUAGES } from "../i18n";
import { Button, ErrorNote, fieldClass } from "./ui";

const SEXES: Sex[] = ["female", "male", "other", "unknown"];
const RELATIONSHIPS: Relationship[] = ["self", "parent", "child", "spouse", "other"];

export function ProfileForm({ onCreated, onCancel }: { onCreated: (p: Profile) => void; onCancel?: () => void }) {
  const { t, i18n } = useTranslation();
  const create = useCreateProfile();
  const [name, setName] = useState("");
  const [sex, setSex] = useState<Sex>("unknown");
  const [dob, setDob] = useState("");
  const [relationship, setRelationship] = useState<Relationship>("self");
  const [language, setLanguage] = useState<Lang>((i18n.resolvedLanguage as Lang) ?? "en");
  const [consent, setConsent] = useState(false);
  const [triedSubmit, setTriedSubmit] = useState(false);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setTriedSubmit(true);
    if (!consent || !name.trim()) return;
    create.mutate(
      {
        display_name: name.trim(),
        sex,
        date_of_birth: dob || null,
        relationship,
        preferred_language: language,
        consent_processing: true,
      },
      { onSuccess: onCreated },
    );
  };

  return (
    <form onSubmit={submit} className="space-y-5" noValidate>
      <h2 className="font-display text-2xl font-bold">{t("profile_form.title")}</h2>

      <div>
        <label htmlFor="pf-name" className="mb-1 block font-medium">{t("profile_form.name")}</label>
        <input id="pf-name" required maxLength={80} value={name} onChange={(e) => setName(e.target.value)}
          className={fieldClass} autoComplete="off" />
      </div>

      <fieldset>
        <legend className="mb-1 font-medium">{t("profile_form.sex")}</legend>
        <div className="flex flex-wrap gap-2">
          {SEXES.map((s) => (
            <label key={s} className="flex cursor-pointer items-center gap-2 rounded-md border border-hairline px-3 py-1.5 has-[:checked]:border-ink has-[:checked]:bg-sunken">
              <input type="radio" name="sex" value={s} checked={sex === s} onChange={() => setSex(s)} className="accent-[var(--accent)]" />
              {t(`profile_form.sex_${s}`)}
            </label>
          ))}
        </div>
      </fieldset>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="pf-dob" className="mb-1 block font-medium">{t("profile_form.dob")}</label>
          <input id="pf-dob" type="date" value={dob} max={new Date().toISOString().slice(0, 10)}
            onChange={(e) => setDob(e.target.value)} className={fieldClass} />
        </div>
        <div>
          <label htmlFor="pf-rel" className="mb-1 block font-medium">{t("profile_form.relationship")}</label>
          <select id="pf-rel" value={relationship} onChange={(e) => setRelationship(e.target.value as Relationship)} className={fieldClass}>
            {RELATIONSHIPS.map((r) => <option key={r} value={r}>{t(`profile_form.rel_${r}`)}</option>)}
          </select>
        </div>
      </div>

      <div>
        <label htmlFor="pf-lang" className="mb-1 block font-medium">{t("profile_form.language")}</label>
        <select id="pf-lang" value={language} onChange={(e) => setLanguage(e.target.value as Lang)} className={fieldClass}>
          {LANGUAGES.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}
        </select>
      </div>

      <div className="rounded-md border border-hairline bg-surface p-4">
        <label className="flex cursor-pointer items-start gap-3">
          <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)}
            className="mt-1 size-4 accent-[var(--accent)]" aria-describedby="pf-consent-note" />
          <span>{t("profile_form.consent")}</span>
        </label>
        <p id="pf-consent-note" className="mt-2 pl-7 text-sm text-muted">{t("profile_form.consent_note")}</p>
        {triedSubmit && !consent && (
          <p role="alert" className="mt-2 pl-7 text-sm text-abnormal">{t("profile_form.consent_needed")}</p>
        )}
      </div>

      {create.isError && <ErrorNote error={create.error} />}

      <div className="flex gap-3">
        <Button type="submit" variant="primary" disabled={create.isPending || !name.trim()}>
          {t("profile_form.create")}
        </Button>
        {onCancel && <Button onClick={onCancel}>{t("common.cancel")}</Button>}
      </div>
    </form>
  );
}
