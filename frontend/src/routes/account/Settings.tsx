import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useNavigate } from "react-router-dom";

import {
  useChangePassword, useDeleteAccount, useLogout, useMe, useResendVerification, useTotpDisable, useTotpEnable,
  useTotpSetup, useUpdateLanguage, type Me,
} from "../../api/auth";
import { useDeleteProfile, useProfiles } from "../../api/hooks";
import type { Lang, Profile } from "../../api/types";
import { Button, Card, ErrorNote, Field, fieldClass, Loading, Notice, PageTitle } from "../../components/ui";
import { LANGUAGES } from "../../i18n";
import { TEXT_SIZES, useTextSize, type TextSize } from "../../lib/theme";
import { MIN_PASSWORD_LENGTH, passwordProblem, useAuthMessage } from "../../lib/account";

export default function Settings() {
  const { t } = useTranslation();
  const me = useMe();
  const { hash } = useLocation();

  useEffect(() => {
    if (hash) document.getElementById(hash.slice(1))?.scrollIntoView?.();
  }, [hash, me.data]);

  if (!me.data) return <Loading />;
  const staff = me.data.role === "reviewer" || me.data.role === "admin";

  return (
    <>
      <PageTitle title={t("settings.title")} />
      {me.data.totp_required && (
        <p role="alert" className="mb-8 max-w-2xl rounded-md border border-borderline/50 bg-borderline/10 px-4 py-3">
          {t("settings.totp_required")}
        </p>
      )}
      <div className="stagger grid max-w-2xl gap-10">
        <AccountSection me={me.data} />
        <SecuritySection me={me.data} staff={staff} />
        {!me.data.totp_required && (
          <>
            <PasswordSection />
            <DataSection />
            <SessionsSection />
            <DeleteAccountSection />
          </>
        )}
      </div>
    </>
  );
}

function Section({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id}-h`} className="scroll-mt-6">
      <h2 id={`${id}-h`} className="mb-3 font-display text-xl font-bold">{title}</h2>
      <Card className="space-y-4 p-5">{children}</Card>
    </section>
  );
}

function AccountSection({ me }: { me: Me }) {
  const { t, i18n } = useTranslation();
  const resend = useResendVerification();
  const language = useUpdateLanguage();
  const change = (lang: Lang) => {
    void i18n.changeLanguage(lang);
    language.mutate(lang);
  };

  return (
    <Section id="account" title={t("settings.account")}>
      <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2">
        <dt className="text-muted">{t("auth.email")}</dt>
        <dd className="break-all">
          {me.email}{" "}
          <span className={me.email_verified ? "text-normal" : "text-borderline"}>
            ({me.email_verified ? t("settings.verified") : t("settings.not_verified")})
          </span>
        </dd>
        {me.role !== "user" && (
          <>
            <dt className="text-muted">{t("settings.role")}</dt>
            <dd>{t(`settings.role_${me.role}`)}</dd>
          </>
        )}
      </dl>
      {!me.email_verified && (
        resend.isSuccess ? <Notice>{t("settings.resent")}</Notice> : (
          <Button onClick={() => resend.mutate()} disabled={resend.isPending}>{t("settings.resend")}</Button>
        )
      )}
      <div>
        <label htmlFor="set-lang" className="mb-1 block font-medium">{t("settings.language")}</label>
        <select id="set-lang" value={me.preferred_language} onChange={(e) => change(e.target.value as Lang)}
          className={`${fieldClass} max-w-xs`} disabled={language.isPending}>
          {LANGUAGES.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}
        </select>
        <p className="mt-1 text-sm text-muted">{t("settings.language_note")}</p>
      </div>
      <TextSizeChoice />
    </Section>
  );
}

function SecuritySection({ me, staff }: { me: Me; staff: boolean }) {
  const { t } = useTranslation();
  const setup = useTotpSetup();
  const enable = useTotpEnable();
  const disable = useTotpDisable();
  const message = useAuthMessage();
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");

  const confirm = (e: FormEvent) => {
    e.preventDefault();
    enable.mutate(code.replace(/\s/g, ""), { onSuccess: () => setup.reset() });
  };
  const turnOff = (e: FormEvent) => {
    e.preventDefault();
    disable.mutate(password, { onSuccess: () => setPassword("") });
  };

  return (
    <Section id="security" title={t("settings.totp_title")}>
      <p className="text-muted">{t("settings.totp_intro")}</p>
      {me.totp_enabled ? (
        <>
          <p className="font-medium text-normal">{t("settings.totp_on")}</p>
          {staff ? (
            <p className="text-sm text-muted">{t("settings.totp_staff")}</p>
          ) : (
            <form onSubmit={turnOff} className="flex flex-wrap items-end gap-3">
              <Field id="totp-off-pw" className="min-w-60 flex-1" label={t("settings.password_to_turn_off")}
                type="password" autoComplete="current-password" value={password}
                onChange={(e) => setPassword(e.target.value)} />
              <Button type="submit" disabled={!password || disable.isPending}>{t("settings.totp_turn_off")}</Button>
            </form>
          )}
          {disable.isError && <ErrorNote message={message(disable.error)} />}
        </>
      ) : setup.data ? (
        <form onSubmit={confirm} className="space-y-4">
          <ol className="list-decimal space-y-1 pl-5">
            <li>{t("settings.totp_step1")}</li>
            <li>{t("settings.totp_step2")}</li>
          </ol>
          <div className="flex flex-wrap items-center gap-6">
            <img src={setup.data.qr_svg} alt={t("settings.totp_qr_alt")} className="size-44 rounded-md border border-hairline" />
            <div className="min-w-0 flex-1 text-sm">
              <p className="text-muted">{t("settings.totp_manual")}</p>
              <code className="mt-1 block break-all rounded bg-sunken px-2 py-1 font-mono tracking-wider">
                {setup.data.secret.replace(/(.{4})/g, "$1 ").trim()}
              </code>
            </div>
          </div>
          <Field id="totp-code" label={t("auth.code")} hint={t("auth.code_hint")} inputMode="numeric"
            autoComplete="one-time-code" maxLength={8} value={code} onChange={(e) => setCode(e.target.value)} />
          {enable.isError && <ErrorNote message={message(enable.error)} />}
          <Button type="submit" variant="primary" disabled={code.replace(/\s/g, "").length < 6 || enable.isPending}>
            {t("settings.totp_confirm")}
          </Button>
        </form>
      ) : (
        <>
          {setup.isError && <ErrorNote message={message(setup.error)} />}
          <Button variant="primary" onClick={() => setup.mutate()} disabled={setup.isPending}>
            {t("settings.totp_set_up")}
          </Button>
        </>
      )}
    </Section>
  );
}

function PasswordSection() {
  const { t } = useTranslation();
  const change = useChangePassword();
  const message = useAuthMessage();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [tried, setTried] = useState(false);
  const problem = passwordProblem(next);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setTried(true);
    if (problem || !current) return;
    change.mutate({ current_password: current, new_password: next }, {
      onSuccess: () => {
        setCurrent("");
        setNext("");
        setTried(false);
      },
    });
  };

  return (
    <Section id="password" title={t("settings.password_title")}>
      <form onSubmit={submit} className="space-y-4" noValidate>
        <Field id="cp-current" label={t("settings.current_password")} type="password" autoComplete="current-password"
          value={current} onChange={(e) => setCurrent(e.target.value)} />
        <Field id="cp-new" label={t("auth.new_password")} type="password" autoComplete="new-password" value={next}
          onChange={(e) => setNext(e.target.value)} hint={t("auth.password_hint", { n: MIN_PASSWORD_LENGTH })}
          error={tried && problem ? t(`auth.pw.${problem}`, { n: MIN_PASSWORD_LENGTH }) : undefined} />
        {change.isError && <ErrorNote message={message(change.error)} />}
        {change.isSuccess && <Notice>{t("settings.password_changed")}</Notice>}
        <Button type="submit" disabled={change.isPending}>{t("settings.change_password")}</Button>
      </form>
    </Section>
  );
}

function DataSection() {
  const { t } = useTranslation();
  const profiles = useProfiles();
  return (
    <Section id="data" title={t("settings.data_title")}>
      <p className="text-muted">{t("settings.data_intro")}</p>
      {profiles.isError && <ErrorNote error={profiles.error} />}
      {profiles.data?.length === 0 && <p className="text-muted">{t("settings.no_people")}</p>}
      <ul className="divide-y divide-hairline">
        {profiles.data?.map((p) => <ProfileDataRow key={p.id} profile={p} />)}
      </ul>
    </Section>
  );
}

function ProfileDataRow({ profile }: { profile: Profile }) {
  const { t } = useTranslation();
  const remove = useDeleteProfile();
  const [confirming, setConfirming] = useState(false);
  const [typed, setTyped] = useState("");

  return (
    <li className="py-3 first:pt-0 last:pb-0">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <Link to={`/p/${profile.id}`} className="font-medium text-link">{profile.display_name}</Link>
        <span className="text-sm text-muted">{t("home.reports", { count: profile.reports })}</span>
        <span className="ml-auto flex gap-2">
          <a href={`/v1/profiles/${profile.id}/export`} download
            className="rounded-md border border-hairline px-3 py-1.5 text-sm no-underline hover:border-ink/40">
            {t("settings.export")}
          </a>
          {!confirming && (
            <Button variant="danger" className="px-3 py-1.5 text-sm" onClick={() => setConfirming(true)}>
              {t("settings.delete_person")}
            </Button>
          )}
        </span>
      </div>
      {confirming && (
        <div className="mt-3 space-y-3 rounded-md border border-abnormal/40 p-4">
          <p>{t("settings.delete_person_warning", { name: profile.display_name })}</p>
          <Field id={`del-${profile.id}`} label={t("settings.type_name", { name: profile.display_name })}
            value={typed} onChange={(e) => setTyped(e.target.value)} autoComplete="off" />
          {remove.isError && <ErrorNote error={remove.error} />}
          <div className="flex gap-3">
            <Button variant="danger" disabled={typed.trim() !== profile.display_name || remove.isPending}
              onClick={() => remove.mutate(profile.id)}>
              {t("settings.delete_person_confirm")}
            </Button>
            <Button onClick={() => { setConfirming(false); setTyped(""); }}>{t("common.cancel")}</Button>
          </div>
        </div>
      )}
    </li>
  );
}

function SessionsSection() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const logoutAll = useLogout(true);
  return (
    <Section id="sessions" title={t("settings.sessions_title")}>
      <p className="text-muted">{t("settings.sessions_intro")}</p>
      <Button onClick={() => logoutAll.mutate(undefined, { onSettled: () => navigate("/login") })}
        disabled={logoutAll.isPending}>
        {t("settings.sign_out_everywhere")}
      </Button>
    </Section>
  );
}

function DeleteAccountSection() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const remove = useDeleteAccount();
  const message = useAuthMessage();
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");

  const submit = (e: FormEvent) => {
    e.preventDefault();
    remove.mutate(password, { onSuccess: () => navigate("/", { replace: true }) });
  };

  return (
    <Section id="delete" title={t("settings.delete_title")}>
      <p className="text-muted">{t("settings.delete_intro")}</p>
      {!open ? (
        <Button variant="danger" onClick={() => setOpen(true)}>{t("settings.delete_account")}</Button>
      ) : (
        <form onSubmit={submit} className="space-y-4">
          <p className="font-medium text-abnormal">{t("settings.delete_warning")}</p>
          <Field id="del-pw" label={t("settings.password_to_delete")} type="password" autoComplete="current-password"
            value={password} onChange={(e) => setPassword(e.target.value)} />
          {remove.isError && <ErrorNote message={message(remove.error)} />}
          <div className="flex gap-3">
            <Button type="submit" variant="danger" disabled={!password || remove.isPending}>
              {t("settings.delete_account_confirm")}
            </Button>
            <Button onClick={() => { setOpen(false); setPassword(""); }}>{t("common.cancel")}</Button>
          </div>
        </form>
      )}
    </Section>
  );
}

function TextSizeChoice() {
  const { t } = useTranslation();
  const [size, setSize] = useTextSize();
  return (
    <fieldset>
      <legend className="mb-1 font-medium">{t("settings.text_size")}</legend>
      <div className="flex flex-wrap gap-2">
        {(Object.keys(TEXT_SIZES) as TextSize[]).map((s) => (
          <label key={s} className="flex cursor-pointer items-center gap-2 rounded-md border border-hairline px-3 py-1.5 has-[:checked]:border-ink has-[:checked]:bg-sunken">
            <input type="radio" name="text-size" checked={size === s} onChange={() => setSize(s)}
              className="accent-[var(--accent)]" />
            <span style={{ fontSize: TEXT_SIZES[s] }}>{t(`settings.size_${s}`)}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
