import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { useLogin } from "../../api/auth";
import { ApiError } from "../../api/client";
import { AuthCard } from "../../components/AuthCard";
import { RedirectIfSignedIn } from "../../components/RequireAuth";
import { Button, ErrorNote, Field } from "../../components/ui";
import { useAuthMessage } from "../../lib/account";

export default function Login() {
  return (
    <RedirectIfSignedIn>
      <LoginForm />
    </RedirectIfSignedIn>
  );
}

function LoginForm() {
  const { t } = useTranslation();
  const login = useLogin();
  const message = useAuthMessage();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [needsCode, setNeedsCode] = useState(false);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    // on success the stored account re-renders RedirectIfSignedIn, which goes on to `next`
    login.mutate(
      { email, password, ...(needsCode && code ? { totp_code: code.replace(/\s/g, "") } : {}) },
      {
        onError: (err) => {
          if (err instanceof ApiError && err.code === "totp_required") setNeedsCode(true);
        },
      },
    );
  };

  const asking = login.error instanceof ApiError && login.error.code === "totp_required";

  return (
    <AuthCard
      title={t("auth.login_title")}
      intro={t("auth.login_intro")}
      footer={
        <>
          <p><Link to="/forgot-password" className="text-link">{t("auth.forgot_link")}</Link></p>
          <p>{t("auth.no_account")} <Link to="/signup" className="text-link">{t("auth.signup_link")}</Link></p>
        </>
      }
    >
      <form onSubmit={submit} className="space-y-4" noValidate>
        <Field id="login-email" label={t("auth.email")} type="email" autoComplete="email" required value={email}
          onChange={(e) => setEmail(e.target.value)} />
        <Field id="login-password" label={t("auth.password")} type="password" autoComplete="current-password" required
          value={password} onChange={(e) => setPassword(e.target.value)} />
        {needsCode && (
          <Field id="login-code" label={t("auth.code")} hint={t("auth.code_hint")} inputMode="numeric"
            autoComplete="one-time-code" maxLength={8} required autoFocus value={code}
            onChange={(e) => setCode(e.target.value)} />
        )}
        {login.isError && !asking && <ErrorNote message={message(login.error)} />}
        <Button type="submit" variant="primary" className="w-full" disabled={login.isPending || !email || !password}>
          {login.isPending ? t("auth.signing_in") : t("auth.sign_in")}
        </Button>
      </form>
    </AuthCard>
  );
}
