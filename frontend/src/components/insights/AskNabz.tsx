import clsx from "clsx";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { useAsk, useDeleteQuestion, useQuestions, type Question } from "../../api/ask";
import { useConsents } from "../../api/hooks";
import type { Result } from "../../api/types";
import { Enso } from "../Enso";
import { IconSeal } from "../icons";
import { Button, Card, ErrorNote, fieldClass } from "../ui";
import { isAbnormal } from "./StatusMark";

const MAX = 300; // mirrors backend/app/explain/ask.py

/**
 * Questions about this report (FR-47). Nabz answers from the confirmed values and MedlinePlus; it gives a fixed
 * reply to anything that asks for a diagnosis, a treatment or help in an emergency, and says so plainly. Every
 * answer shown is the checked text; this component only lays it out.
 */
export function AskNabz({ reportId, profileId, results }: { reportId: string; profileId: string; results: Result[] }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const questions = useQuestions(reportId);
  const ask = useAsk(reportId);
  const consents = useConsents(profileId).data;
  const [text, setText] = useState("");
  const end = useRef<HTMLDivElement>(null);
  const withAi = Boolean(consents?.find((c) => c.purpose === "external_ai")?.granted);

  const outside = results.filter((r) => isAbnormal(r.status));
  const suggestions = [
    ...(outside.length > 0 ? [t("ask.suggest_outside")] : []),
    ...(outside.length > 0 ? outside : results).slice(0, 2).map((r) => t("ask.suggest_measures", { test: r.test_name })),
    ...(results.some((r) => r.change?.fraction != null) ? [t("ask.suggest_changed")] : []),
  ];

  const send = (question: string) => {
    const q = question.trim();
    if (q.length < 3 || ask.isPending) return;
    setText("");
    ask.mutate({ question: q, language: lang });
  };
  const submit = (e: FormEvent) => {
    e.preventDefault();
    send(text);
  };

  // keep the newest answer in view, without moving the page when it first loads
  const count = (questions.data?.length ?? 0) + (ask.isPending ? 1 : 0);
  const seen = useRef<number | null>(null);
  useEffect(() => {
    if (seen.current !== null && count > seen.current) end.current?.scrollIntoView?.({ behavior: "smooth", block: "nearest" });
    if (questions.data) seen.current = count;
  }, [count, questions.data]);

  return (
    <Card className="mt-6 p-5 sm:p-6">
      <h2 className="flex items-center gap-2.5 font-display text-2xl font-bold"><IconSeal name="chat" />{t("ask.title")}</h2>
      <p className="mt-0.5 max-w-prose text-sm text-muted">{t("ask.intro")}</p>

      {questions.isError && <div className="mt-4"><ErrorNote error={questions.error} /></div>}
      <ol className="mt-4 space-y-5" aria-label={t("ask.thread")}>
        {questions.data?.map((q) => <li key={q.id}><Exchange q={q} reportId={reportId} /></li>)}
        {ask.isPending && (
          <li>
            <Asked text={ask.variables.question} />
            <div className="mt-2 flex items-center gap-3 text-muted"><Enso label={t("ask.writing")} size={44} /></div>
          </li>
        )}
      </ol>
      <div ref={end} />

      {ask.isError && <div className="mt-4"><ErrorNote error={ask.error} /></div>}

      <div className="mt-4 flex flex-wrap gap-2">
        {suggestions.map((s) => (
          <button key={s} type="button" disabled={ask.isPending} onClick={() => send(s)}
            className="btn rounded-full border border-hairline bg-surface px-3 py-1 text-left text-sm hover:border-ink/40 disabled:opacity-50">
            {s}
          </button>
        ))}
      </div>

      <form onSubmit={submit} className="mt-3 flex gap-2">
        <label className="min-w-0 flex-1">
          <span className="sr-only">{t("ask.label")}</span>
          <input value={text} maxLength={MAX} onChange={(e) => setText(e.target.value)} className={fieldClass}
            placeholder={t("ask.placeholder")} autoComplete="off" />
        </label>
        <Button type="submit" variant="primary" disabled={text.trim().length < 3 || ask.isPending}>{t("ask.send")}</Button>
      </form>
      <p className="mt-2 text-sm text-muted">{t(withAi ? "ask.note_ai" : "ask.note_rules")}</p>
    </Card>
  );
}

function Asked({ text }: { text: string }) {
  return (
    <p className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-br-sm bg-sunken px-4 py-2">{text}</p>
  );
}

function Exchange({ q, reportId }: { q: Question; reportId: string }) {
  const { t } = useTranslation();
  const remove = useDeleteQuestion(reportId);
  const refused = q.mode === "refusal";
  const lines = q.answer.split("\n").filter(Boolean);
  return (
    <article className="slide-in" lang={q.language}>
      <Asked text={q.question} />
      <div className={clsx("mt-2 max-w-[92%] rounded-2xl rounded-bl-sm border px-4 py-3",
        refused ? "border-borderline/50 bg-borderline/5" : "border-hairline bg-surface")}>
        {refused && (
          <p className="mb-1 flex items-center gap-1.5 text-sm font-medium text-borderline">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6"
              strokeLinecap="round" aria-hidden="true"><circle cx="8" cy="8" r="6.2" /><path d="M3.8 12.2 12.2 3.8" /></svg>
            {t(`ask.refusal_${q.refusal ?? "cannot_answer"}`)}
          </p>
        )}
        <div className="space-y-1.5">
          {lines.map((line, i) => line.startsWith("• ")
            ? <p key={i} className="tabular flex gap-2"><span aria-hidden="true">•</span><span>{line.slice(2)}</span></p>
            : <p key={i}>{line}</p>)}
        </div>
        {q.sources.length > 0 && (
          <p className="mt-2 text-sm text-muted">
            {t("explain.sources")}:{" "}
            {q.sources.map((s, i) => (
              <span key={s.label}>
                {i > 0 && ", "}
                {s.url ? <a href={s.url} target="_blank" rel="noreferrer" className="text-link">{s.title}</a> : s.title}
              </span>
            ))}
          </p>
        )}
        <p className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
          <span>{t(`ask.by_${q.mode}`)}</span>
          {q.mode === "knowledge" && (q.reason === "validation" || q.reason === "provider_error" || q.reason === "critical") && (
            <span>{t(`ask.reason_${q.reason}`)}</span>
          )}
          <button type="button" className="ml-auto hover:text-abnormal hover:underline" disabled={remove.isPending}
            aria-label={t("ask.delete_label", { question: q.question })} onClick={() => remove.mutate(q.id)}>
            {t("records.delete")}
          </button>
        </p>
      </div>
    </article>
  );
}
