import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { useReportNote } from "../../api/hooks";
import { Button, fieldClass } from "../ui";

/** The person's own note on a report ("not fasting", "new medicine"), shown with its results and on the timeline. */
export function ReportNote({ reportId, profileId, note }: { reportId: string; profileId: string; note: string | null }) {
  const { t } = useTranslation();
  const save = useReportNote(reportId, profileId);
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(note ?? "");

  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate(text, { onSuccess: () => setEditing(false) });
  };

  if (!editing) {
    return (
      <div className="mb-6 flex flex-wrap items-baseline gap-2 text-sm">
        {note ? (
          <p className="rounded-md bg-sunken px-3 py-1.5"><span className="text-muted">{t("note.label")}:</span> {note}</p>
        ) : null}
        <button type="button" className="text-link hover:underline" onClick={() => { setText(note ?? ""); setEditing(true); }}>
          {note ? t("note.edit") : t("note.add")}
        </button>
      </div>
    );
  }
  return (
    <form onSubmit={submit} className="mb-6 flex max-w-2xl flex-wrap items-end gap-2">
      <label className="min-w-64 flex-1">
        <span className="mb-1 block text-sm font-medium">{t("note.label")}</span>
        <input value={text} maxLength={500} onChange={(e) => setText(e.target.value)} className={fieldClass}
          placeholder={t("note.placeholder")} autoFocus />
      </label>
      <Button type="submit" variant="primary" disabled={save.isPending}>{t("common.save")}</Button>
      <Button onClick={() => setEditing(false)}>{t("common.cancel")}</Button>
    </form>
  );
}
