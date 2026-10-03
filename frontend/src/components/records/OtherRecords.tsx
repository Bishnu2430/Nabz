import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { recordFileUrl, recordImageUrl, useAddRecord, useDeleteRecord, useRecords } from "../../api/hooks";
import type { HealthRecord, RecordKind } from "../../api/types";
import { formatDate } from "../../lib/format";
import { useToast } from "../Toast";
import { Button, Card, Empty, ErrorNote, SectionTitle, fieldClass } from "../ui";
import { ImagingViewer } from "./ImagingViewer";

const KINDS: RecordKind[] = ["imaging", "prescription", "discharge", "vaccination", "other"];

/**
 * Other records kept with the person's lab reports: X-ray and MRI reports, prescriptions, discharge summaries.
 * Stored and shown on the timeline; Nabz doesn't read or explain them.
 */
export function OtherRecords({ profileId }: { profileId: string }) {
  const { t } = useTranslation();
  const records = useRecords(profileId);
  const [adding, setAdding] = useState(false);

  return (
    <section aria-labelledby="records-h" className="mt-10">
      <SectionTitle id="records-h" icon="film" title={t("records.title")} className="mb-2"
        action={!adding && <Button onClick={() => setAdding(true)}>{t("records.add")}</Button>} />
      <p className="mb-4 max-w-prose text-sm text-muted">{t("records.intro")}</p>
      {adding && <AddRecord profileId={profileId} onDone={() => setAdding(false)} />}
      {records.isError && <ErrorNote error={records.error} />}
      {records.data?.length === 0 && !adding && <Empty icon="film">{t("records.empty")}</Empty>}
      <ul className="stagger grid gap-3 sm:grid-cols-2">
        {records.data?.map((r) => <li key={r.id}><RecordCard record={r} profileId={profileId} /></li>)}
      </ul>
    </section>
  );
}

function RecordCard({ record, profileId }: { record: HealthRecord; profileId: string }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const remove = useDeleteRecord(profileId);
  const toast = useToast();
  const [confirming, setConfirming] = useState(false);
  const [viewing, setViewing] = useState(false);
  return (
    <Card className="lift h-full overflow-hidden">
      {record.has_image && (
        <button type="button" onClick={() => setViewing(true)} aria-label={t("viewer.open", { title: record.title })}
          className="group relative block h-44 w-full overflow-hidden bg-black">
          <img src={recordImageUrl(record.id)} alt="" loading="lazy"
            className="size-full object-contain opacity-90 transition group-hover:scale-105 group-hover:opacity-100" />
          <span className="absolute bottom-2 right-2 rounded-full bg-black/70 px-3 py-1 text-sm text-[#ede3d1]">
            {t("viewer.view")}
          </span>
        </button>
      )}
      {viewing && <ImagingViewer record={record} onClose={() => setViewing(false)} />}
      <div className="flex items-start gap-3 p-4">
        <KindIcon kind={record.kind} />
        <div className="min-w-0 flex-1">
          <p className="text-sm text-muted">{t(`records.kind_${record.kind}`)}</p>
          <h3 className="font-medium">{record.title}</h3>
          <p className="text-sm text-muted">
            {[record.record_date && formatDate(record.record_date, lang), record.facility].filter(Boolean).join(" · ")}
          </p>
          {record.impression?.[0] && <p className="mt-1 text-sm font-medium">{record.impression[0]}</p>}
          {record.notes && <p className="mt-1 text-sm">{record.notes}</p>}
          <div className="mt-2 flex flex-wrap items-center gap-3 text-sm">
            <a href={recordFileUrl(record.id)} target="_blank" rel="noreferrer" className="text-link">
              {t("records.open")} ({record.mime_type === "application/pdf" ? "PDF" : t("records.image")},{" "}
              {Math.max(1, Math.round(record.size_bytes / 1024))} KB)
            </a>
            {confirming ? (
              <>
                <Button variant="danger" className="px-2 py-0.5 text-sm" disabled={remove.isPending}
                  onClick={() => remove.mutate(record.id, { onSuccess: () => toast(t("toast.record_deleted")) })}>
                  {t("records.delete_confirm")}
                </Button>
                <button type="button" className="text-muted hover:underline" onClick={() => setConfirming(false)}>
                  {t("common.cancel")}
                </button>
              </>
            ) : (
              <button type="button" className="text-muted hover:text-abnormal hover:underline"
                onClick={() => setConfirming(true)}>{t("records.delete")}</button>
            )}
          </div>
        </div>
      </div>
    </Card>
  );
}

function AddRecord({ profileId, onDone }: { profileId: string; onDone: () => void }) {
  const { t } = useTranslation();
  const add = useAddRecord(profileId);
  const toast = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [kind, setKind] = useState<RecordKind>("imaging");
  const [title, setTitle] = useState("");
  const [date, setDate] = useState("");
  const [facility, setFacility] = useState("");
  const [notes, setNotes] = useState("");

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!file || !title.trim()) return;
    add.mutate({ file, kind, title: title.trim(), record_date: date || undefined, facility: facility.trim() || undefined,
      notes: notes.trim() || undefined }, {
      onSuccess: () => {
        toast(t("toast.record_saved"));
        onDone();
      },
    });
  };

  return (
    <Card className="mb-4 p-5">
      <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2" noValidate>
        <label className="sm:col-span-2">
          <span className="mb-1 block font-medium">{t("records.file")}</span>
          <input type="file" accept="application/pdf,image/jpeg,image/png,image/webp" required
            onChange={(e) => setFile(e.target.files?.[0] ?? null)} className="block w-full text-sm" />
          <span className="mt-1 block text-sm text-muted">{t("records.file_hint")}</span>
        </label>
        <label>
          <span className="mb-1 block font-medium">{t("records.kind")}</span>
          <select value={kind} onChange={(e) => setKind(e.target.value as RecordKind)} className={fieldClass}>
            {KINDS.map((k) => <option key={k} value={k}>{t(`records.kind_${k}`)}</option>)}
          </select>
        </label>
        <label>
          <span className="mb-1 block font-medium">{t("records.name")}</span>
          <input value={title} maxLength={120} required onChange={(e) => setTitle(e.target.value)} className={fieldClass}
            placeholder={t("records.name_placeholder")} />
        </label>
        <label>
          <span className="mb-1 block font-medium">{t("records.date")}</span>
          <input type="date" value={date} max={new Date().toISOString().slice(0, 10)}
            onChange={(e) => setDate(e.target.value)} className={fieldClass} />
        </label>
        <label>
          <span className="mb-1 block font-medium">{t("records.facility")}</span>
          <input value={facility} maxLength={120} onChange={(e) => setFacility(e.target.value)} className={fieldClass} />
        </label>
        <label className="sm:col-span-2">
          <span className="mb-1 block font-medium">{t("records.notes")}</span>
          <input value={notes} maxLength={1000} onChange={(e) => setNotes(e.target.value)} className={fieldClass} />
        </label>
        {add.isError && <div className="sm:col-span-2"><ErrorNote error={add.error} /></div>}
        <div className="flex gap-3 sm:col-span-2">
          <Button type="submit" variant="primary" disabled={!file || !title.trim() || add.isPending}>
            {t("records.save")}
          </Button>
          <Button onClick={onDone}>{t("common.cancel")}</Button>
        </div>
      </form>
    </Card>
  );
}

function KindIcon({ kind }: { kind: RecordKind }) {
  const common = { width: 28, height: 28, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.6,
    strokeLinecap: "round" as const, strokeLinejoin: "round" as const, "aria-hidden": true, className: "shrink-0 text-muted" };
  switch (kind) {
    case "imaging": // a film with a bone
      return <svg {...common}><rect x="3" y="3" width="18" height="18" rx="2" /><path d="M9 7.5a1.5 1.5 0 1 0-1 2.6L14 16a1.5 1.5 0 1 0 2.6-1L10.6 9A1.5 1.5 0 0 0 9 7.5Z" /></svg>;
    case "prescription":
      return <svg {...common}><path d="M6 3h8l4 4v14H6z" /><path d="M9 11h6M9 15h4" /></svg>;
    case "discharge":
      return <svg {...common}><path d="M4 21V8l8-5 8 5v13" /><path d="M12 10v6M9 13h6" /></svg>;
    case "vaccination":
      return <svg {...common}><path d="m17 3 4 4M19 5l-9 9M8 12l4 4M5 19l3-3M14 7l3 3" /></svg>;
    default:
      return <svg {...common}><path d="M6 3h9l3 3v15H6z" /></svg>;
  }
}
