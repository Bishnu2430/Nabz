import { useState, type FormEvent } from "react";
import { Trans, useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { useRegister } from "../../api/auth";
import type { Lang } from "../../api/types";
import { AuthCard } from "../../components/AuthCard";
import { RedirectIfSignedIn } from "../../components/RequireAuth";
import { Button, ErrorNote, Field } from "../../components/ui";
import { MIN_PASSWORD_LENGTH, passwordProblem, useAuthMessage } from "../../lib/account";
import { MailHint } from "./MailHint";

export default function Signup() {
  return (
    <RedirectIfSignedIn>
      <SignupForm />
    </RedirectIfSignedIn>
  );
}

function SignupForm() {
  const { t, i18n } = useTranslation();
  const register = useRegister();
  const message = useAuthMessage();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [tried, setTried] = useState(false);

  const problem = passwordProblem(password, email);
  const submit = (e: FormEvent) => {
    e.preventDefault();
    setTried(true);
    if (problem || !email.includes("@")) return;
    register.mutate({ email: email.trim(), password, preferred_language: (i18n.resolvedLanguage ?? "en") as Lang });
  };

  if (register.isSuccess) {
    return (
      <AuthCard title={t("auth.check_email_title")} intro={t("auth.check_email_body", { email: email.trim() })}
        footer={<p><Link to="/login" className="text-link">{t("auth.to_sign_in")}</Link></p>}>
        <MailHint />
      </AuthCard>
    );
  }

  return (
    <AuthCard
      title={t("auth.signup_title")}
      intro={t("auth.signup_intro")}
      footer={<p>{t("auth.have_account")} <Link to="/login" className="text-link">{t("auth.sign_in")}</Link></p>}
    >
      <form onSubmit={submit} className="space-y-4" noValidate>
        <Field id="su-email" label={t("auth.email")} type="email" autoComplete="email" required value={email}
          onChange={(e) => setEmail(e.target.value)}
          error={tried && !email.includes("@") ? t("auth.err.email") : undefined} />
        <Field id="su-password" label={t("auth.new_password")} type="password" autoComplete="new-password" required
          value={password} onChange={(e) => setPassword(e.target.value)}
          hint={t("auth.password_hint", { n: MIN_PASSWORD_LENGTH })}
          error={tried && problem ? t(`auth.pw.${problem}`, { n: MIN_PASSWORD_LENGTH }) : undefined} />
        {register.isError && <ErrorNote message={message(register.error)} />}
        <p className="text-sm text-muted">
          <Trans i18nKey="auth.signup_accept" components={{
            terms: <Link to="/terms" className="text-link" />, privacy: <Link to="/privacy" className="text-link" />,
            safety: <Link to="/safety" className="text-link" />,
          }} />
        </p>
        <Button type="submit" variant="primary" className="w-full" disabled={register.isPending}>
          {t("auth.create_account")}
        </Button>
      </form>
    </AuthCard>
  );
}
