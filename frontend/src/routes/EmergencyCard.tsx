import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { useEmergencyCard, useSaveEmergency, type EmergencyCard as CardData, type EmergencyContact, type EmergencyInfo } from "../api/care";
import { useExact } from "../components/exact/exact";
import { StatusIcon } from "../components/insights/StatusMark";
import { useToast } from "../components/Toast";
import { Button, Card, ErrorNote, Loading, PageTitle, fieldClass } from "../components/ui";
import { formatDate, formatWithUnit } from "../lib/format";
import NotFound from "./NotFound";

const BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];
const MAX_CONTACTS = 3;

/**
 * A card to print and keep in a wallet: who the person is, what the family typed about allergies, conditions and
 * medicines, who to call, and the latest lab results outside their range. The QR code holds the same text, so a
 * phone camera can read it with no network. Nabz prints what was typed; it adds nothing of its own.
 */
export default function EmergencyCard() {
  const { id = "" } = useParams();
  const { t } = useTranslation();
  const card = useEmergencyCard(id);
  const [withResults, setWithResults] = useState(true);

  if (card.isPending) return <Loading />;
  if (card.isError) {
    if (card.error instanceof ApiError && card.error.status === 404) return <NotFound />;
    return <ErrorNote error={card.error} onRetry={() => void card.refetch()} />;
  }
  const data = card.data;

  return (
    <>
      <div className="print:hidden">
        <Link to={`/p/${id}`} className="text-link">← {data.person.display_name}</Link>
        <PageTitle title={t("card.title")} subtitle={t("card.intro")}
          action={<Button variant="primary" onClick={() => window.print()}>{t("card.print")}</Button>} />
      </div>
      <div className="grid gap-8 lg:grid-cols-2 print:block">
        <div className="print:hidden">
          <CardForm key={JSON.stringify(data.info)} profileId={id} info={data.info} />
        </div>
        <div>
          <CardFace data={data} withResults={withResults} />
          <div className="mt-4 space-y-3 print:hidden">
            {data.out_of_range.length > 0 && (
              <label className="flex items-start gap-2">
                <input type="checkbox" checked={withResults} onChange={(e) => setWithResults(e.target.checked)} className="mt-1" />
                <span>{t("card.include_results")}</span>
              </label>
            )}
            <details className="text-sm">
              <summary className="cursor-pointer text-muted">{t("card.qr_shows")}</summary>
              <pre className="mt-2 whitespace-pre-wrap rounded-md border border-hairline bg-sunken p-3 font-sans">{data.qr_text}</pre>
            </details>
            <p className="max-w-prose text-sm text-muted">{t("card.note")}</p>
          </div>
        </div>
      </div>
    </>
  );
}

function CardFace({ data, withResults }: { data: CardData; withResults: boolean }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const { describe } = useExact();
  const { person, info } = data;
  const who = [person.age != null && t("summary.age", { count: person.age }),
    (person.sex === "female" || person.sex === "male") && t(`profile_form.sex_${person.sex}`)].filter(Boolean).join(" · ");
  const rows: [string, string | null][] = [
    [t("card.allergies"), info.allergies], [t("card.conditions"), info.conditions],
    [t("card.medicines"), info.medicines], [t("card.doctor"), info.doctor],
  ];
  const empty = !info.blood_group && rows.every(([, v]) => !v) && info.contacts.length === 0;

  return (
    // a printed card: fixed ink-on-white colours in both themes
    <article aria-label={t("card.title")}
      className="pop mx-auto max-w-md overflow-hidden rounded-xl border-2 border-[#b42318] bg-white text-[#1f1d1b] shadow-lg print:mx-0 print:shadow-none">
      <header className="flex items-center justify-between gap-3 bg-[#b42318] px-5 py-2.5 text-white">
        <p className="text-sm font-bold uppercase tracking-widest">{t("card.heading")}</p>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M9 2h6v7h7v6h-7v7H9v-7H2V9h7z" /></svg>
      </header>
      <div className="px-5 py-4">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h2 className="font-display text-2xl font-bold leading-tight">{person.display_name}</h2>
            {who && <p className="text-[#5c564e]">{who}</p>}
          </div>
          {info.blood_group && (
            <div className="shrink-0 rounded-lg border-2 border-[#b42318] px-3 py-1 text-center">
              <p className="text-[10px] font-semibold uppercase tracking-wide text-[#5c564e]">{t("card.blood_group")}</p>
              <p className="text-2xl font-bold leading-none text-[#b42318]">{info.blood_group.replace("-", "−")}</p>
            </div>
          )}
        </div>

        {empty && <p className="mt-4 text-[#5c564e]">{t("card.empty")}</p>}
        <dl className="mt-3 space-y-1.5 text-sm">
          {rows.map(([label, value]) => value && (
            <div key={label}>
              <dt className="text-[11px] font-semibold uppercase tracking-wide text-[#5c564e]">{label}</dt>
              <dd className="whitespace-pre-line">{value}</dd>
            </div>
          ))}
        </dl>

        {info.contacts.length > 0 && (
          <div className="mt-3 rounded-lg bg-[#f5efe4] px-3 py-2 text-sm">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-[#5c564e]">{t("card.call")}</p>
            <ul>
              {info.contacts.map((c) => (
                <li key={`${c.name}${c.phone}`} className="flex flex-wrap justify-between gap-x-3">
                  <span>{c.name}{c.relation ? ` (${c.relation})` : ""}</span>
                  <a href={`tel:${c.phone.replace(/[^\d+]/g, "")}`} className="tabular font-semibold text-[#1f1d1b] no-underline">{c.phone}</a>
                </li>
              ))}
            </ul>
          </div>
        )}

        {withResults && data.out_of_range.length > 0 && (
          <div className="mt-3 text-sm">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-[#5c564e]">
              {t("card.results", { date: formatDate(data.last_tested, lang) })}
            </p>
            <ul>
              {data.out_of_range.slice(0, 6).map((v) => (
                <li key={v.test_code} className="flex gap-1.5">
                  <span className="mt-1 shrink-0 text-[#b42318]"><StatusIcon status={v.status} /></span>
                  <span>
                    <span className="font-medium">{v.test_name}</span>{" "}
                    <span className="tabular font-semibold">{formatWithUnit(v)}</span>
                    <span className="text-[#5c564e]">, {describe(v)} · {formatDate(v.date, lang)}</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="mt-4 flex items-center gap-3 border-t border-[#d9cfbd] pt-3">
          <img src={data.qr_svg} alt={t("card.qr_alt")} className="size-24 shrink-0" />
          <p className="text-xs text-[#5c564e]">{t("card.qr_hint")}<br />{t("card.updated", { date: formatDate(new Date().toISOString().slice(0, 10), lang) })}</p>
        </div>
      </div>
    </article>
  );
}

function CardForm({ profileId, info }: { profileId: string; info: EmergencyInfo }) {
  const { t } = useTranslation();
  const save = useSaveEmergency(profileId);
  const toast = useToast();
  const [form, setForm] = useState({
    blood_group: info.blood_group ?? "", allergies: info.allergies ?? "", conditions: info.conditions ?? "",
    medicines: info.medicines ?? "", doctor: info.doctor ?? "",
  });
  const [contacts, setContacts] = useState<EmergencyContact[]>(
    info.contacts.length ? info.contacts.map((c) => ({ ...c, relation: c.relation ?? "" })) : [{ name: "", phone: "", relation: "" }]);
  const set = (field: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [field]: e.target.value });
  const setContact = (i: number, field: keyof EmergencyContact, value: string) =>
    setContacts(contacts.map((c, j) => (j === i ? { ...c, [field]: value } : c)));
  const half = contacts.some((c) => Boolean(c.name.trim()) !== Boolean(c.phone.trim()));

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (half) return;
    const text = (v: string) => v.trim() || null;
    save.mutate({
      blood_group: text(form.blood_group), allergies: text(form.allergies), conditions: text(form.conditions),
      medicines: text(form.medicines), doctor: text(form.doctor),
      contacts: contacts.filter((c) => c.name.trim() && c.phone.trim())
        .map((c) => ({ name: c.name.trim(), phone: c.phone.trim(), relation: c.relation?.trim() || null })),
    }, { onSuccess: () => toast(t("card.saved")) });
  };

  return (
    <Card className="p-5">
      <form onSubmit={submit} className="space-y-4" noValidate>
        <label className="block max-w-40">
          <span className="mb-1 block font-medium">{t("card.blood_group")}</span>
          <select value={form.blood_group} onChange={set("blood_group")} className={fieldClass}>
            <option value="">{t("card.not_known")}</option>
            {BLOOD_GROUPS.map((g) => <option key={g} value={g}>{g.replace("-", "−")}</option>)}
          </select>
        </label>
        <label className="block">
          <span className="mb-1 block font-medium">{t("card.allergies")}</span>
          <input value={form.allergies} maxLength={300} onChange={set("allergies")} className={fieldClass}
            placeholder={t("card.allergies_placeholder")} />
        </label>
        <label className="block">
          <span className="mb-1 block font-medium">{t("card.conditions")}</span>
          <input value={form.conditions} maxLength={300} onChange={set("conditions")} className={fieldClass}
            placeholder={t("card.conditions_placeholder")} />
          <span className="mt-1 block text-sm text-muted">{t("card.conditions_hint")}</span>
        </label>
        <label className="block">
          <span className="mb-1 block font-medium">{t("card.medicines")}</span>
          <textarea value={form.medicines} maxLength={400} rows={2} onChange={set("medicines")} className={fieldClass}
            placeholder={t("card.medicines_placeholder")} />
        </label>
        <label className="block">
          <span className="mb-1 block font-medium">{t("card.doctor")}</span>
          <input value={form.doctor} maxLength={120} onChange={set("doctor")} className={fieldClass}
            placeholder={t("card.doctor_placeholder")} />
        </label>

        <fieldset>
          <legend className="mb-1 font-medium">{t("card.call")}</legend>
          <ul className="space-y-2">
            {contacts.map((c, i) => (
              <li key={i} className="grid grid-cols-[1fr_1fr] gap-2 sm:grid-cols-[1.2fr_1fr_0.8fr_auto]">
                <input value={c.name} maxLength={80} onChange={(e) => setContact(i, "name", e.target.value)} className={fieldClass}
                  aria-label={t("card.contact_name", { n: i + 1 })} placeholder={t("profile_form.name")} />
                <input value={c.phone} maxLength={30} inputMode="tel" onChange={(e) => setContact(i, "phone", e.target.value)}
                  className={fieldClass} aria-label={t("card.contact_phone", { n: i + 1 })} placeholder={t("card.phone")} />
                <input value={c.relation ?? ""} maxLength={40} onChange={(e) => setContact(i, "relation", e.target.value)}
                  className={fieldClass} aria-label={t("card.contact_relation", { n: i + 1 })} placeholder={t("card.relation")} />
                <button type="button" className="justify-self-start text-sm text-muted hover:text-abnormal hover:underline"
                  aria-label={t("card.contact_remove", { n: i + 1 })}
                  onClick={() => setContacts(contacts.length > 1 ? contacts.filter((_, j) => j !== i) : [{ name: "", phone: "", relation: "" }])}>
                  {t("review.remove")}
                </button>
              </li>
            ))}
          </ul>
          {contacts.length < MAX_CONTACTS && (
            <Button variant="quiet" className="mt-1 px-0" onClick={() => setContacts([...contacts, { name: "", phone: "", relation: "" }])}>
              {t("card.contact_add")}
            </Button>
          )}
          {half && <p className="mt-1 text-sm text-abnormal">{t("card.contact_half")}</p>}
        </fieldset>

        {save.isError && <ErrorNote error={save.error} />}
        <Button type="submit" variant="primary" disabled={save.isPending || half}>{t("card.save")}</Button>
      </form>
    </Card>
  );
}
