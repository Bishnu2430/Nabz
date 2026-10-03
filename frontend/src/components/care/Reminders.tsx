import clsx from "clsx";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { reminderCalendarUrl, useAddReminder, useReminderAction, useReminders, type Reminder } from "../../api/care";
import { formatDate } from "../../lib/format";
import { useToast } from "../Toast";
import { Button, Card, ErrorNote, fieldClass } from "../ui";

const REPEATS = [0, 1, 3, 6, 12] as const;

/** Whole days from today to an ISO date (negative when past), by calendar date. */
export function daysUntil(iso: string, today = new Date()): number {
  const start = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate());
  return Math.round((Date.parse(`${iso}T00:00:00Z`) - start) / 86_400_000);
}

export function useDueText() {
  const { t } = useTranslation();
  return (iso: string) => {
    const d = daysUntil(iso);
    if (d === 0) return t("reminders.today");
    return d > 0 ? t("reminders.in_days", { count: d }) : t("reminders.overdue", { count: -d });
  };
}

/**
 * Reminders the family sets for themselves, for example to repeat a test when the doctor said. Nabz emails the
 * account on the date and offers a calendar file; it never proposes the date.
 */
export function Reminders({ profileId }: { profileId: string }) {
  const { t } = useTranslation();
  const reminders = useReminders(profileId);
  const [adding, setAdding] = useState(false);
  const open = reminders.data?.filter((r) => !r.done_at) ?? [];
  const done = reminders.data?.filter((r) => r.done_at) ?? [];

  return (
    <section aria-labelledby="reminders-h" className="mb-10">
      <div className="mb-2 flex flex-wrap items-baseline justify-between gap-3">
        <h2 id="reminders-h" className="font-display text-xl font-bold">{t("reminders.title")}</h2>
        {!adding && <Button onClick={() => setAdding(true)}>{t("reminders.add")}</Button>}
      </div>
      <p className="mb-4 max-w-prose text-sm text-muted">{t("reminders.intro")}</p>
      {adding && <ReminderForm profileId={profileId} onDone={() => setAdding(false)} />}
      {reminders.isError && <ErrorNote error={reminders.error} />}
      {reminders.data?.length === 0 && !adding && <p className="text-muted">{t("reminders.empty")}</p>}
      <ul className="stagger grid gap-3 sm:grid-cols-2">
        {open.map((r) => <li key={r.id}><ReminderCard reminder={r} profileId={profileId} /></li>)}
      </ul>
      {done.length > 0 && (
        <details className="mt-3 text-sm">
          <summary className="cursor-pointer text-muted">{t("reminders.done_count", { count: done.length })}</summary>
          <ul className="mt-2 grid gap-3 sm:grid-cols-2">
            {done.map((r) => <li key={r.id}><ReminderCard reminder={r} profileId={profileId} /></li>)}
          </ul>
        </details>
      )}
    </section>
  );
}

function ReminderCard({ reminder: r, profileId }: { reminder: Reminder; profileId: string }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const act = useReminderAction(profileId);
  const toast = useToast();
  const due = useDueText();
  const days = daysUntil(r.due_on);
  const isDone = Boolean(r.done_at);
  return (
    <Card className={clsx("h-full p-4", isDone && "opacity-70")}>
      <div className="flex items-start gap-3">
        <BellIcon overdue={!isDone && days < 0} />
        <div className="min-w-0 flex-1">
          <h3 className={clsx("font-medium", isDone && "line-through")}>{r.title}</h3>
          <p className="text-sm">
            <span className="tabular">{formatDate(r.due_on, lang)}</span>
            {!isDone && (
              <span className={clsx("ml-2", days < 0 ? "font-medium text-abnormal" : days <= 14 ? "text-borderline" : "text-muted")}>
                {due(r.due_on)}
              </span>
            )}
          </p>
          {r.repeat_months && <p className="text-sm text-muted">{t("reminders.repeats", { count: r.repeat_months })}</p>}
          {r.note && <p className="mt-1 text-sm">{r.note}</p>}
          {r.sent_at && !isDone && <p className="text-sm text-muted">{t("reminders.emailed", { date: formatDate(r.sent_at, lang) })}</p>}
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
            {isDone ? (
              <button type="button" className="text-link hover:underline" onClick={() => act.mutate({ id: r.id, action: "undo" })}>
                {t("reminders.undo")}
              </button>
            ) : (
              <>
                <button type="button" className="font-medium text-link hover:underline" disabled={act.isPending}
                  onClick={() => act.mutate({ id: r.id, action: "done" }, { onSuccess: () => toast(t("reminders.marked_done")) })}>
                  {t("reminders.done")}
                </button>
                <a href={reminderCalendarUrl(r.id)} download className="text-link">{t("reminders.calendar")}</a>
                <button type="button" className="text-link hover:underline" disabled={act.isPending}
                  onClick={() => act.mutate({ id: r.id, action: "send" }, { onSuccess: () => toast(t("reminders.email_sent")) })}>
                  {t("reminders.email_now")}
                </button>
              </>
            )}
            <button type="button" className="text-muted hover:text-abnormal hover:underline" disabled={act.isPending}
              onClick={() => act.mutate({ id: r.id, action: "delete" })}>
              {t("records.delete")}
            </button>
          </div>
        </div>
      </div>
    </Card>
  );
}

/** A new reminder; `preset` fills it for a test ("Repeat HbA1c"). */
export function ReminderForm({ profileId, onDone, preset }: {
  profileId: string;
  onDone: () => void;
  preset?: { title: string; test_code?: string };
}) {
  const { t } = useTranslation();
  const add = useAddReminder(profileId);
  const toast = useToast();
  const [title, setTitle] = useState(preset?.title ?? "");
  const [due, setDue] = useState("");
  const [repeat, setRepeat] = useState<number>(0);
  const [note, setNote] = useState("");
  const today = new Date().toISOString().slice(0, 10);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !due) return;
    add.mutate({ title: title.trim(), due_on: due, test_code: preset?.test_code, repeat_months: repeat || undefined,
      note: note.trim() || undefined }, {
      onSuccess: () => {
        toast(t("reminders.saved"));
        onDone();
      },
    });
  };

  return (
    <Card className="rise mb-4 p-5">
      <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2" noValidate>
        <label className="sm:col-span-2">
          <span className="mb-1 block font-medium">{t("reminders.what")}</span>
          <input value={title} maxLength={120} onChange={(e) => setTitle(e.target.value)} className={fieldClass}
            placeholder={t("reminders.what_placeholder")} />
        </label>
        <label>
          <span className="mb-1 block font-medium">{t("reminders.when")}</span>
          <input type="date" value={due} min={today} onChange={(e) => setDue(e.target.value)} className={fieldClass} />
        </label>
        <label>
          <span className="mb-1 block font-medium">{t("reminders.repeat")}</span>
          <select value={repeat} onChange={(e) => setRepeat(Number(e.target.value))} className={fieldClass}>
            {REPEATS.map((m) => <option key={m} value={m}>{m ? t("reminders.every", { count: m }) : t("reminders.once")}</option>)}
          </select>
        </label>
        <label className="sm:col-span-2">
          <span className="mb-1 block font-medium">{t("records.notes")}</span>
          <input value={note} maxLength={300} onChange={(e) => setNote(e.target.value)} className={fieldClass}
            placeholder={t("reminders.note_placeholder")} />
        </label>
        <p className="text-sm text-muted sm:col-span-2">{t("reminders.own_date")}</p>
        {add.isError && <div className="sm:col-span-2"><ErrorNote error={add.error} /></div>}
        <div className="flex gap-3 sm:col-span-2">
          <Button type="submit" variant="primary" disabled={!title.trim() || !due || add.isPending}>{t("reminders.save")}</Button>
          <Button onClick={onDone}>{t("common.cancel")}</Button>
        </div>
      </form>
    </Card>
  );
}

function BellIcon({ overdue }: { overdue: boolean }) {
  return (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true" className={clsx("shrink-0", overdue ? "text-abnormal" : "text-muted")}>
      <path d="M6 9a6 6 0 1 1 12 0c0 5 2 6 2 6H4s2-1 2-6Z" /><path d="M10 19a2 2 0 0 0 4 0" />
    </svg>
  );
}
