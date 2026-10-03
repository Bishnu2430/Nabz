import clsx from "clsx";
import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { useMe, useUpdateLanguage } from "../api/auth";
import { ApiError } from "../api/client";
import { useProfiles, useSampleReport } from "../api/hooks";
import type { Lang, Profile } from "../api/types";
import { PrivacyChoices } from "../components/PrivacyChoices";
import { ProfileForm } from "../components/ProfileForm";
import { ReportProgress } from "../components/ReportProgress";
import { Icon, IconSeal, type IconName } from "../components/icons";
import { Button, Card, ErrorNote, Loading } from "../components/ui";
import { LANGUAGES } from "../i18n";

const STEPS = ["language", "about", "person", "privacy", "report"] as const;
type Step = (typeof STEPS)[number];

/**
 * The first-run walkthrough: language, what Nabz is and is not, the first person (with their consent), the two
 * optional privacy choices, and the first report (their own, or a sample). Shown when the account has no one in
 * it yet; it can be taken again from the settings.
 */
export default function Welcome() {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const profiles = useProfiles();
  const [understood, setUnderstood] = useState(false);

  const asked = Number(params.get("step")) || 1;
  const index = Math.min(Math.max(asked, 1), STEPS.length) - 1;
  const profile = profiles.data?.find((p) => p.id === params.get("person"));
  // the last two steps are about a person: without one, the walkthrough waits at "first person"
  const step: Step = !profile && index > 2 ? "person" : STEPS[index];
  const at = STEPS.indexOf(step);
  const go = (n: number, person = profile?.id) =>
    setParams({ step: String(n + 1), ...(person ? { person } : {}) });

  if (profiles.isPending) return <Loading />;
  if (profiles.isError) return <ErrorNote error={profiles.error} onRetry={() => void profiles.refetch()} />;

  return (
    <div className="mx-auto max-w-2xl">
      <p className="text-sm text-muted">{t("welcome.title")}</p>
      <ol className="mb-6 mt-2 flex items-center gap-2" aria-label={t("welcome.step", { n: at + 1, total: STEPS.length })}>
        {STEPS.map((s, i) => (
          <li key={s} aria-current={i === at ? "step" : undefined} className="flex flex-1 flex-col gap-1.5">
            <span className={clsx("h-1.5 rounded-full transition-colors duration-500", i <= at ? "bg-accent" : "bg-hairline")} />
            <span className={clsx("hidden text-xs sm:block", i === at ? "font-medium text-ink" : "text-muted")}>
              {t(`welcome.steps.${s}`)}
            </span>
          </li>
        ))}
      </ol>

      <div key={step} className="slide-in">
        {step === "language" && <LanguageStep onNext={() => go(1)} />}
        {step === "about" && (
          <Frame icon="shield" title={t("welcome.about_title")} onBack={() => go(0)} onNext={() => go(2)} nextDisabled={!understood}>
            <div className="grid gap-4 sm:grid-cols-2">
              <Points title={t("welcome.is_title")} tone="text-normal" mark="M3.5 8.5l3 3 6-7"
                items={[t("welcome.is_1"), t("welcome.is_2"), t("welcome.is_3")]} />
              <Points title={t("welcome.not_title")} tone="text-abnormal" mark="M4 4l8 8M12 4l-8 8"
                items={[t("welcome.not_1"), t("welcome.not_2"), t("welcome.not_3")]} />
            </div>
            <label className="mt-5 flex cursor-pointer items-start gap-3 rounded-md border border-hairline bg-surface p-4">
              <input type="checkbox" checked={understood} onChange={(e) => setUnderstood(e.target.checked)}
                className="mt-1 size-4 accent-[var(--accent)]" />
              <span>{t("welcome.understand")}</span>
            </label>
            <p className="mt-3 text-sm text-muted">
              <Link to="/safety" className="text-link">{t("legal.safety_title")}</Link>
              {" · "}
              <Link to="/privacy" className="text-link">{t("legal.privacy_title")}</Link>
            </p>
          </Frame>
        )}
        {step === "person" && (
          <Frame icon="person" title={t("welcome.person_title")} body={t("welcome.person_body")} onBack={() => go(1)}>
            {profiles.data.length > 0 && (
              <div className="mb-5">
                <ul className="flex flex-wrap gap-2">
                  {profiles.data.map((p) => (
                    <li key={p.id}>
                      <Button onClick={() => go(3, p.id)}>{t("welcome.continue_with", { name: p.display_name })}</Button>
                    </li>
                  ))}
                </ul>
                <p className="mt-4 text-sm text-muted">{t("welcome.or_add")}</p>
              </div>
            )}
            <ProfileForm onCreated={(p: Profile) => go(3, p.id)} />
          </Frame>
        )}
        {step === "privacy" && profile && (
          <Frame icon="lock" title={t("welcome.privacy_title", { name: profile.display_name })} body={t("welcome.privacy_body")}
            onBack={() => go(2)} onNext={() => go(4)}>
            <div className="-mt-10 [&_h2]:sr-only"><PrivacyChoices profileId={profile.id} /></div>
          </Frame>
        )}
        {step === "report" && profile && <ReportStep profile={profile} onBack={() => go(3)} />}
      </div>
    </div>
  );
}

function Frame({ title, body, children, onBack, onNext, nextDisabled, icon }: {
  title: string; body?: string; children: ReactNode; onBack?: () => void; onNext?: () => void; nextDisabled?: boolean;
  icon?: IconName;
}) {
  const { t } = useTranslation();
  return (
    <Card className="corner-pattern p-6 sm:p-8">
      <h1 className="flex items-center gap-3 font-display text-2xl font-bold sm:text-3xl">
        {icon && <IconSeal name={icon} size={22} className="icon-seal-lg" />}{title}
      </h1>
      {body && <p className="mt-2 text-muted">{body}</p>}
      <div className="mt-6">{children}</div>
      {(onBack || onNext) && (
        <div className="mt-8 flex items-center justify-between gap-3">
          {onBack ? <Button variant="quiet" className="px-0" onClick={onBack}>← {t("common.back")}</Button> : <span />}
          {onNext && <Button variant="primary" onClick={onNext} disabled={nextDisabled}>{t("welcome.next")}</Button>}
        </div>
      )}
    </Card>
  );
}

function LanguageStep({ onNext }: { onNext: () => void }) {
  const { t, i18n } = useTranslation();
  const me = useMe().data;
  const save = useUpdateLanguage();
  const choose = (lang: Lang) => {
    void i18n.changeLanguage(lang);
    if (me && me.preferred_language !== lang) save.mutate(lang);
  };
  return (
    <Frame icon="globe" title={t("welcome.language_title")} body={t("welcome.language_body")} onNext={onNext}>
      <div role="radiogroup" aria-label={t("nav.language")} className="grid gap-3 sm:grid-cols-3">
        {LANGUAGES.map((l) => {
          const on = i18n.resolvedLanguage === l.code;
          return (
            <button key={l.code} type="button" role="radio" aria-checked={on} lang={l.code} onClick={() => choose(l.code)}
              className={clsx("btn lift rounded-lg border px-4 py-5 text-center font-display text-2xl font-bold",
                on ? "border-accent bg-accent/10" : "border-hairline bg-surface hover:border-ink/40")}>
              {l.label}
            </button>
          );
        })}
      </div>
    </Frame>
  );
}

function Points({ title, items, tone, mark }: { title: string; items: string[]; tone: string; mark: string }) {
  return (
    <div className="rounded-lg border border-hairline bg-surface p-4">
      <h2 className="mb-2 font-medium">{title}</h2>
      <ul className="space-y-2 text-sm">
        {items.map((item) => (
          <li key={item} className="flex gap-2">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"
              strokeLinejoin="round" aria-hidden="true" className={clsx("mt-0.5 shrink-0", tone)}><path d={mark} /></svg>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function ReportStep({ profile, onBack }: { profile: Profile; onBack: () => void }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const sample = useSampleReport();
  // a sample tried before is still there: open it rather than refusing
  const existing = sample.error instanceof ApiError && sample.error.status === 409 ? String(sample.error.body.report_id ?? "") : "";

  if (sample.isPending || sample.data) {
    return <ReportProgress reportId={sample.data?.report_id} sending={sample.isPending} onRetry={() => sample.reset()} />;
  }
  return (
    <Frame icon="report" title={t("welcome.report_title")} body={t("welcome.report_body", { name: profile.display_name })} onBack={onBack}>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="flex flex-col rounded-lg border border-hairline bg-surface p-5">
          <h2 className="flex items-center gap-2 font-display text-lg font-bold"><Icon name="upload" className="text-accent" />{t("welcome.upload_title")}</h2>
          <p className="mb-4 mt-1 flex-1 text-sm text-muted">{t("welcome.upload_body")}</p>
          <Button variant="primary" onClick={() => navigate(`/p/${profile.id}/upload`)}>{t("person.upload")}</Button>
        </div>
        <div className="flex flex-col rounded-lg border border-hairline bg-surface p-5">
          <h2 className="flex items-center gap-2 font-display text-lg font-bold"><Icon name="sample" className="text-accent" />{t("welcome.sample_title")}</h2>
          <p className="mb-4 mt-1 flex-1 text-sm text-muted">{t("welcome.sample_body")}</p>
          <Button onClick={() => sample.mutate(profile.id)}>{t("welcome.sample_start")}</Button>
        </div>
      </div>
      <div className="mt-4 space-y-3">
        {existing ? (
          <p role="alert" className="rounded-md border border-borderline/40 bg-borderline/5 px-4 py-3">
            {t("welcome.sample_exists")}{" "}
            <Link to={`/r/${existing}/review`} className="text-link">{t("upload.open_existing")}</Link>
          </p>
        ) : (
          sample.isError && <ErrorNote error={sample.error} />
        )}
        <p><Link to={`/p/${profile.id}`} className="text-link">{t("welcome.later")}</Link></p>
      </div>
    </Frame>
  );
}
