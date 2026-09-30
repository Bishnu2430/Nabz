import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../../api/client";
import { useExplanation, useFeedback, useNarrate, useRequestExplanation, useSetConsent } from "../../api/hooks";
import type { Explanation, Result } from "../../api/types";
import { LANGUAGES } from "../../i18n";
import { Enso } from "../Enso";
import { Button, Card, ErrorNote } from "../ui";

/**
 * The plain-language explanation (FR-21 – FR-26), in the app's language. The generated text is shown only after
 * it passed Nabz's checks; otherwise the explanation built from the values alone is shown, and the card says why.
 */
export function ExplanationCard({ reportId, profileId, results }: { reportId: string; profileId: string; results: Result[] }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const state = useExplanation(reportId, lang);
  const request = useRequestExplanation(reportId);
  const setConsent = useSetConsent(profileId);
  const names = Object.fromEntries(results.map((r) => [r.test_code, r.test_name]));

  const allowAndRewrite = async () => {
    await setConsent.mutateAsync({ purpose: "external_ai", granted: true });
    await request.mutateAsync({ language: lang, regenerate: true });
  };

  let body;
  if (state.isPending) body = null;
  else if (state.isError) body = <ErrorNote error={state.error} />;
  else if (state.data.state === "pending" && !state.data.explanation) {
    body = <div className="py-6 text-center"><Enso label={t("explain.writing")} size={96} /></div>;
  } else if (!state.data.explanation) {
    body = (
      <div className="space-y-3">
        <p className="text-muted">{t("explain.none")}</p>
        <Button variant="primary" disabled={request.isPending} onClick={() => request.mutate({ language: lang })}>
          {t("explain.write_in", { language: LANGUAGES.find((l) => l.code === lang)?.label ?? lang })}
        </Button>
      </div>
    );
  } else {
    body = (
      <ExplanationBody explanation={state.data.explanation} names={names} profileId={profileId}
        rewriting={state.data.state === "pending"} onAllowAi={allowAndRewrite} busy={setConsent.isPending || request.isPending} />
    );
  }

  return (
    <Card className="p-6">
      <h2 className="font-display text-2xl font-bold">{t("explain.title")}</h2>
      <div className="mt-3">{body}</div>
    </Card>
  );
}

function ExplanationBody({ explanation: e, names, profileId, rewriting, onAllowAi, busy }: {
  explanation: Explanation;
  names: Record<string, string>;
  profileId: string;
  rewriting: boolean;
  onAllowAi: () => void;
  busy: boolean;
}) {
  const { t } = useTranslation();
  const labelIndex = Object.fromEntries(e.sources.map((s, i) => [s.label, i + 1]));
  return (
    <div className="space-y-6">
      {e.source === "template" && e.reason && (
        <div className="rounded-md border border-hairline bg-sunken px-4 py-3 text-sm">
          <p>{t("explain.template_note")}</p>
          {["no_consent", "validation", "provider_error", "critical"].includes(e.reason) && (
            <p className="mt-1 text-muted">{t(`explain.reason_${e.reason}`)}</p>
          )}
          {e.reason === "no_consent" && (
            <Button variant="secondary" className="mt-3" disabled={busy || rewriting} onClick={onAllowAi}>
              {t("explain.allow_ai")}
            </Button>
          )}
        </div>
      )}
      {rewriting && <p role="status" className="text-sm text-muted">{t("explain.writing")}</p>}

      <p className="max-w-prose whitespace-pre-line text-lg leading-relaxed">{e.summary}</p>

      {e.per_test.map((p) => (
        <section key={p.test_code} aria-labelledby={`ex-${p.test_code}`} className="max-w-prose">
          <h3 id={`ex-${p.test_code}`} className="font-display text-xl font-bold">{names[p.test_code] ?? p.test_code}</h3>
          {p.what_it_measures && <p className="mt-1 text-muted">{p.what_it_measures}</p>}
          <p className="mt-2 leading-relaxed">
            {p.what_this_result_means}
            {p.citations.filter((c) => labelIndex[c]).map((c) => (
              <sup key={c} className="ml-0.5"><a href={`#src-${labelIndex[c]}`} className="text-link">[{labelIndex[c]}]</a></sup>
            ))}
          </p>
        </section>
      ))}

      {e.doctor_questions.length > 0 && (
        <section aria-labelledby="ex-questions">
          <h3 id="ex-questions" className="font-display text-xl font-bold">{t("explain.questions")}</h3>
          <ul className="mt-2 list-disc space-y-1 pl-6">
            {e.doctor_questions.map((q) => <li key={q}>{q}</li>)}
          </ul>
        </section>
      )}

      <Narration explanation={e} profileId={profileId} />

      {e.sources.length > 0 && (
        <section aria-labelledby="ex-sources" className="text-sm">
          <h3 id="ex-sources" className="font-medium">{t("explain.sources")}</h3>
          <ol className="mt-1 space-y-0.5">
            {e.sources.map((s, i) => (
              <li key={s.label} id={`src-${i + 1}`}>
                [{i + 1}] {s.url ? <a href={s.url} target="_blank" rel="noreferrer" className="text-link">{s.title}</a> : s.title}
              </li>
            ))}
          </ol>
          <p className="mt-1 text-muted">{t("explain.source_note")}</p>
        </section>
      )}

      <p className="border-t border-hairline pt-4 text-sm text-muted">{t("explain.disclaimer")}</p>
      <Feedback explanationId={e.id} />
    </div>
  );
}

function Narration({ explanation, profileId }: { explanation: Explanation; profileId: string }) {
  const { t } = useTranslation();
  const narrate = useNarrate();
  const setConsent = useSetConsent(profileId);
  const [url, setUrl] = useState<string | null>(explanation.has_audio ? `/v1/explanations/${explanation.id}/audio` : null);
  const needsConsent = narrate.error instanceof ApiError && narrate.error.status === 409;

  const listen = () => narrate.mutate(explanation.id, { onSuccess: (r) => setUrl(r.url) });
  const allow = async () => {
    await setConsent.mutateAsync({ purpose: "voice", granted: true });
    listen();
  };

  if (url) return <audio controls autoPlay={!explanation.has_audio} src={url} className="w-full max-w-md" />;
  return (
    <div className="space-y-2">
      {needsConsent ? (
        <div className="rounded-md border border-hairline bg-sunken px-4 py-3 text-sm">
          <p>{t("explain.voice_consent")}</p>
          <Button className="mt-2" onClick={() => void allow()} disabled={setConsent.isPending || narrate.isPending}>
            {t("explain.allow_voice")}
          </Button>
        </div>
      ) : (
        <Button onClick={listen} disabled={narrate.isPending}>
          <svg aria-hidden="true" width="16" height="16" viewBox="0 0 16 16"><path d="M4 2.5v11l9-5.5z" fill="currentColor" /></svg>
          {narrate.isPending ? t("explain.preparing_audio") : t("explain.listen")}
        </Button>
      )}
      {narrate.isError && !needsConsent && <p role="alert" className="text-sm text-abnormal">{t("explain.audio_failed")}</p>}
    </div>
  );
}

function Feedback({ explanationId }: { explanationId: string }) {
  const { t } = useTranslation();
  const feedback = useFeedback();
  if (feedback.isSuccess) return <p className="text-sm text-muted">{t("explain.thanks")}</p>;
  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="text-muted">{t("explain.helpful")}</span>
      <Button className="px-3 py-1 text-sm" disabled={feedback.isPending}
        onClick={() => feedback.mutate({ id: explanationId, helpful: true })}>{t("explain.yes")}</Button>
      <Button className="px-3 py-1 text-sm" disabled={feedback.isPending}
        onClick={() => feedback.mutate({ id: explanationId, helpful: false })}>{t("explain.no")}</Button>
    </div>
  );
}
