import clsx from "clsx";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { ApiError } from "../../api/client";
import { useExplanation, useFeedback, useNarrate, useRequestExplanation, useSetConsent } from "../../api/hooks";
import type { Explanation, Result, Source, TestExplanation } from "../../api/types";
import { LANGUAGES } from "../../i18n";
import { formatRange, formatWithUnit } from "../../lib/format";
import { Enso } from "../Enso";
import { useExact } from "../exact/exact";
import { bulletRest, matchBullet, parseSummary } from "../explain/summary";
import { Collapse } from "../motion";
import { IconSeal } from "../icons";
import { Button, Card, ErrorNote } from "../ui";
import { RangeBar } from "./RangeBar";
import { STATUS_COLOR, StatusMark, isAbnormal } from "./StatusMark";

/**
 * The plain-language explanation (FR-21 – FR-26), in the app's language. The generated text is shown only after
 * it passed Nabz's checks; otherwise the explanation built from the values alone is shown, and the card says why.
 *
 * It reads as cards, not paragraphs: one per out-of-range result with its value drawn against the lab's range,
 * what it can go along with, and the longer explanation folded behind "More about this test". Every sentence
 * shown is the checked text; only the layout is added here.
 */
export function ExplanationCard({ reportId, profileId, results, activeTest, onActiveTest }: {
  reportId: string;
  profileId: string;
  results: Result[];
  /** The test highlighted on the original report beside this card. */
  activeTest?: string | null;
  onActiveTest?: (code: string | null) => void;
}) {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const state = useExplanation(reportId, lang);
  const request = useRequestExplanation(reportId);
  const setConsent = useSetConsent(profileId);

  const allowAndRewrite = async () => {
    await setConsent.mutateAsync({ purpose: "external_ai", granted: true });
    await request.mutateAsync({ language: lang, regenerate: true });
  };

  const explanation = state.data?.explanation ?? null;
  let body;
  if (state.isPending) body = <ExplanationSkeleton />;
  else if (state.isError) body = <ErrorNote error={state.error} />;
  else if (state.data.state === "pending" && !explanation) {
    body = <div className="py-6 text-center"><Enso label={t("explain.writing")} size={96} /></div>;
  } else if (!explanation) {
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
      <ExplanationBody explanation={explanation} results={results} profileId={profileId}
        rewriting={state.data.state === "pending"} onAllowAi={allowAndRewrite} busy={setConsent.isPending || request.isPending}
        activeTest={activeTest ?? null} onActiveTest={onActiveTest} />
    );
  }

  return (
    <Card className="p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2.5 font-display text-2xl font-bold"><IconSeal name="book" />{t("explain.title")}</h2>
          {explanation && (
            <p className="mt-0.5 text-sm text-muted">
              {explanation.source === "model" ? t("explain.by_model") : t("explain.by_template")}
            </p>
          )}
        </div>
        {explanation && <Narration explanation={explanation} profileId={profileId} />}
      </div>
      <div className="mt-4">{body}</div>
    </Card>
  );
}

function ExplanationSkeleton() {
  return (
    <div className="space-y-3" aria-hidden="true">
      {[0, 1, 2].map((i) => <div key={i} className="skeleton h-24 rounded-lg" />)}
    </div>
  );
}

function ExplanationBody({ explanation: e, results, profileId, rewriting, onAllowAi, busy, activeTest, onActiveTest }: {
  explanation: Explanation;
  results: Result[];
  profileId: string;
  rewriting: boolean;
  onAllowAi: () => void;
  busy: boolean;
  activeTest: string | null;
  onActiveTest?: (code: string | null) => void;
}) {
  const { t } = useTranslation();
  const parts = parseSummary(e.summary);
  const byCode = new Map(results.map((r) => [r.test_code, r]));
  const explained = new Map(e.per_test.map((p) => [p.test_code, p]));
  const labelIndex = Object.fromEntries(e.sources.map((s, i) => [s.label, i + 1]));

  // one card per bullet that names a result; a bullet that names none stays a plain line
  const cards: { result: Result; rest: string }[] = [];
  const loose: string[] = [];
  for (const bullet of parts.bullets) {
    const result = matchBullet(bullet, results);
    if (result && !cards.some((c) => c.result.test_code === result.test_code)) cards.push({ result, rest: bulletRest(bullet) });
    else loose.push(bullet);
  }
  // an out-of-range result the summary didn't list still gets its card
  for (const p of e.per_test) {
    const result = byCode.get(p.test_code);
    if (result && isAbnormal(result.status) && !cards.some((c) => c.result.test_code === p.test_code)) {
      cards.push({ result, rest: "" });
    }
  }
  const carded = new Set(cards.map((c) => c.result.test_code));
  const others = e.per_test.filter((p) => !carded.has(p.test_code) && byCode.has(p.test_code));
  const unfold = cards.length <= 4; // a few results: show everything; many: keep each card short

  return (
    <div className="space-y-6">
      {e.source === "template" && e.reason && (
        <div className="flex gap-3 rounded-lg border border-hairline bg-sunken px-4 py-3 text-sm">
          <InfoIcon />
          <div>
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
        </div>
      )}
      {rewriting && <p role="status" className="text-sm text-muted">{t("explain.writing")}</p>}

      {parts.intro.map((line) => (
        <p key={line} className={clsx("leading-relaxed", parts.bullets.length ? "font-medium" : "text-lg")}>{line}</p>
      ))}

      {cards.length > 0 && (
        <ul className="space-y-3">
          {cards.map(({ result, rest }, i) => (
            <li key={result.test_code} className="rise" style={{ animationDelay: `${Math.min(i, 8) * 60}ms` }}>
              <ResultExplained result={result} notice={rest} detail={explained.get(result.test_code)} profileId={profileId}
                labelIndex={labelIndex} active={activeTest === result.test_code} onShow={onActiveTest}
                defaultOpen={unfold} />
            </li>
          ))}
        </ul>
      )}
      {loose.length > 0 && (
        <ul className="list-disc space-y-1 pl-6">{loose.map((b) => <li key={b}>{b}</li>)}</ul>
      )}

      {parts.closing.map((line) => (
        <p key={line} className="flex gap-3 rounded-lg border border-accent/30 bg-accent/5 px-4 py-3 font-medium">
          <DoctorIcon />
          <span>{line}</span>
        </p>
      ))}

      {others.length > 0 && <OtherResults items={others} byCode={byCode} profileId={profileId} labelIndex={labelIndex} />}

      {e.doctor_questions.length > 0 && <Questions questions={e.doctor_questions} />}

      {e.sources.length > 0 && <Sources sources={e.sources} />}

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-hairline pt-4">
        <p className="max-w-prose text-sm text-muted">{t("explain.disclaimer")}</p>
        <Feedback explanationId={e.id} />
      </div>
    </div>
  );
}

/** One out-of-range result: its number against the range, what it can go along with, and the longer text folded. */
function ResultExplained({ result: r, notice, detail, profileId, labelIndex, active, onShow, defaultOpen }: {
  result: Result;
  notice: string;
  detail?: TestExplanation;
  profileId: string;
  labelIndex: Record<string, number>;
  active: boolean;
  onShow?: (code: string | null) => void;
  defaultOpen: boolean;
}) {
  const { t } = useTranslation();
  const { describe } = useExact();
  const [open, setOpen] = useState(defaultOpen);
  const ref = useRef<HTMLDivElement>(null);
  const range = formatRange(r.ref_low, r.ref_high);
  const hasDetail = Boolean(detail && (detail.what_it_measures || detail.what_this_result_means));

  // chosen on the report page beside the card: bring the card into view
  useEffect(() => {
    if (active) ref.current?.scrollIntoView?.({ block: "nearest", behavior: "smooth" });
  }, [active]);

  return (
    <div ref={ref} className={clsx("overflow-hidden rounded-lg border bg-surface transition-shadow",
      active ? "border-accent shadow-[0_0_0_3px_color-mix(in_srgb,var(--accent)_18%,transparent)]" : "border-hairline")}>
      <div className="flex">
        <div aria-hidden="true" className="w-1.5 shrink-0" style={{ background: STATUS_COLOR[r.status] }} />
        <div className="min-w-0 flex-1 p-4">
          <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1">
            <div className="min-w-0">
              <StatusMark status={r.status} />
              <h3 className="font-display text-lg font-bold leading-snug">
                <Link to={`/p/${profileId}/tests/${r.test_code}`} className="text-ink no-underline hover:text-link hover:underline">
                  {r.test_name}
                </Link>
              </h3>
            </div>
            <p className="tabular text-right text-2xl font-semibold leading-none">{formatWithUnit(r)}</p>
          </div>

          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
            <RangeBar value={Number(r.value)} low={r.ref_low == null ? null : Number(r.ref_low)}
              high={r.ref_high == null ? null : Number(r.ref_high)} status={r.status} />
            <span className={clsx("font-medium", isAbnormal(r.status) ? "text-abnormal" : "text-normal")}>{describe(r)}</span>
            {range && <span className="tabular text-muted">{t("organ.range", { range })}</span>}
          </div>

          {notice && (
            <div className="mt-3 flex gap-2.5 text-[0.95rem] leading-relaxed">
              <NoticeIcon />
              <p>{notice}</p>
            </div>
          )}

          {(hasDetail || onShow) && (
            <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1 text-sm">
              {hasDetail && (
                <button type="button" aria-expanded={open} onClick={() => setOpen((o) => !o)}
                  className="inline-flex items-center gap-1 text-link hover:underline">
                  <Chevron open={open} />
                  {open ? t("explain.less") : t("explain.more")}
                </button>
              )}
              {onShow && (
                <button type="button" aria-pressed={active} onClick={() => onShow(active ? null : r.test_code)}
                  className="inline-flex items-center gap-1 text-link hover:underline">
                  <TargetIcon />
                  {t("explain.show_on_report")}
                </button>
              )}
            </div>
          )}

          {hasDetail && (
            <Collapse open={open}>
              <DetailText detail={detail!} labelIndex={labelIndex} className="mt-3 border-t border-hairline pt-3" />
            </Collapse>
          )}
        </div>
      </div>
    </div>
  );
}

function DetailText({ detail, labelIndex, className }: {
  detail: TestExplanation;
  labelIndex: Record<string, number>;
  className?: string;
}) {
  const { t } = useTranslation();
  return (
    <dl className={clsx("space-y-2 text-[0.95rem] leading-relaxed", className)}>
      {detail.what_it_measures && (
        <div>
          <dt className="text-sm font-semibold text-muted">{t("explain.measures")}</dt>
          <dd>{detail.what_it_measures}</dd>
        </div>
      )}
      {detail.what_this_result_means && (
        <div>
          <dt className="text-sm font-semibold text-muted">{t("explain.means")}</dt>
          <dd>
            {detail.what_this_result_means}
            {detail.citations.filter((c) => labelIndex[c]).map((c) => (
              <sup key={c} className="ml-0.5"><a href={`#src-${labelIndex[c]}`} className="text-link">[{labelIndex[c]}]</a></sup>
            ))}
          </dd>
        </div>
      )}
    </dl>
  );
}

/** Results the explanation covers that weren't called out above (usually those in range): one line each, unfolding. */
function OtherResults({ items, byCode, profileId, labelIndex }: {
  items: TestExplanation[];
  byCode: Map<string, Result>;
  profileId: string;
  labelIndex: Record<string, number>;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState<string | null>(null);
  return (
    <section aria-labelledby="ex-others">
      <h3 id="ex-others" className="mb-2 font-display text-xl font-bold">{t("explain.others", { count: items.length })}</h3>
      <ul className="divide-y divide-hairline rounded-lg border border-hairline">
        {items.map((p) => {
          const r = byCode.get(p.test_code)!;
          const isOpen = open === p.test_code;
          return (
            <li key={p.test_code}>
              <button type="button" aria-expanded={isOpen} onClick={() => setOpen(isOpen ? null : p.test_code)}
                className="flex w-full items-center gap-3 px-4 py-2.5 text-left hover:bg-sunken/60">
                <Chevron open={isOpen} />
                <span className="min-w-0 flex-1 font-medium">{r.test_name}</span>
                <span className="tabular">{formatWithUnit(r)}</span>
                <StatusMark status={r.status} />
              </button>
              <Collapse open={isOpen}>
                <div className="px-4 pb-3 pl-11">
                  <DetailText detail={p} labelIndex={labelIndex} />
                  <Link to={`/p/${profileId}/tests/${r.test_code}`} className="mt-1 inline-block text-sm text-link">
                    {t("organ.full_history")} →
                  </Link>
                </div>
              </Collapse>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function Questions({ questions }: { questions: string[] }) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(questions.map((q, i) => `${i + 1}. ${q}`).join("\n"));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard unavailable: the list is on the page to read or print */
    }
  };
  return (
    <section aria-labelledby="ex-questions">
      <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
        <h3 id="ex-questions" className="font-display text-xl font-bold">{t("explain.questions")}</h3>
        <button type="button" onClick={() => void copy()} className="text-sm text-link hover:underline" aria-live="polite">
          {copied ? t("explain.copied") : t("explain.copy")}
        </button>
      </div>
      <ol className="space-y-2">
        {questions.map((q, i) => (
          <li key={q} className="flex gap-3 rounded-lg bg-sunken px-4 py-2.5">
            <span aria-hidden="true" className="grid size-6 shrink-0 place-items-center rounded-full bg-accent text-sm font-semibold text-accent-ink">
              {i + 1}
            </span>
            <span>{q}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}

function Sources({ sources }: { sources: Source[] }) {
  const { t } = useTranslation();
  return (
    <details className="group text-sm">
      <summary className="cursor-pointer list-none font-medium text-link hover:underline">
        <span className="inline-flex items-center gap-1">
          <span className="transition-transform group-open:rotate-90" aria-hidden="true">›</span>
          {t("explain.sources")} ({sources.length})
        </span>
      </summary>
      <ol className="mt-2 space-y-0.5">
        {sources.map((s, i) => (
          <li key={s.label} id={`src-${i + 1}`}>
            [{i + 1}] {s.url ? <a href={s.url} target="_blank" rel="noreferrer" className="text-link">{s.title}</a> : s.title}
          </li>
        ))}
      </ol>
      <p className="mt-1 text-muted">{t("explain.source_note")}</p>
    </details>
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

  if (url) return <audio controls autoPlay={!explanation.has_audio} src={url} className="h-10 w-full max-w-xs" />;
  return (
    <div className="space-y-2 text-right">
      {needsConsent ? (
        <div className="max-w-xs rounded-md border border-hairline bg-sunken px-4 py-3 text-left text-sm">
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

const ICON = { width: 18, height: 18, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.7,
  strokeLinecap: "round" as const, strokeLinejoin: "round" as const, "aria-hidden": true };

function Chevron({ open }: { open: boolean }) {
  return (
    <svg {...ICON} width={14} height={14} className={clsx("shrink-0 transition-transform duration-200", open && "rotate-90")}>
      <path d="m9 5 7 7-7 7" />
    </svg>
  );
}

function InfoIcon() {
  return <svg {...ICON} className="mt-0.5 shrink-0 text-muted"><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 7.6v.4" /></svg>;
}

function NoticeIcon() {
  // an eye: "what you might notice"
  return (
    <svg {...ICON} className="mt-0.5 shrink-0 text-borderline">
      <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z" /><circle cx="12" cy="12" r="2.6" />
    </svg>
  );
}

function DoctorIcon() {
  // a stethoscope
  return (
    <svg {...ICON} className="mt-0.5 shrink-0 text-accent">
      <path d="M6 3v6a4 4 0 0 0 8 0V3M10 13v3a5 5 0 0 0 10 0v-2" /><circle cx="20" cy="12" r="2" />
    </svg>
  );
}

function TargetIcon() {
  return <svg {...ICON} width={14} height={14}><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="2.5" /><path d="M12 2v3M12 19v3M2 12h3M19 12h3" /></svg>;
}
