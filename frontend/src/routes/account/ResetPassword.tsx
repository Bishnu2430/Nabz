import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";

import { useResetPassword } from "../../api/auth";
import { AuthCard } from "../../components/AuthCard";
import { Button, ErrorNote, Field, Notice } from "../../components/ui";
import { MIN_PASSWORD_LENGTH, passwordProblem, useAuthMessage } from "../../lib/account";

export default function ResetPassword() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const reset = useResetPassword();
  const message = useAuthMessage();
  const [password, setPassword] = useState("");
  const [again, setAgain] = useState("");
  const [tried, setTried] = useState(false);

  const problem = passwordProblem(password);
  const mismatch = again !== password;
  const submit = (e: FormEvent) => {
    e.preventDefault();
    setTried(true);
    if (!problem && !mismatch) reset.mutate({ token, password });
  };

  if (reset.isSuccess) {
    return (
      <AuthCard title={t("auth.reset_title")}>
        <Notice>{t("auth.reset_done")}</Notice>
        <Link to="/login" className="mt-6 inline-block text-link">{t("auth.to_sign_in")}</Link>
      </AuthCard>
    );
  }

  return (
    <AuthCard title={t("auth.reset_title")} intro={t("auth.reset_intro")}
      footer={<p><Link to="/forgot-password" className="text-link">{t("auth.reset_new_link")}</Link></p>}>
      {!token ? (
        <ErrorNote message={t("auth.err.token")} />
      ) : (
        <form onSubmit={submit} className="space-y-4" noValidate>
          <Field id="rp-password" label={t("auth.new_password")} type="password" autoComplete="new-password" required
            value={password} onChange={(e) => setPassword(e.target.value)}
            hint={t("auth.password_hint", { n: MIN_PASSWORD_LENGTH })}
            error={tried && problem ? t(`auth.pw.${problem}`, { n: MIN_PASSWORD_LENGTH }) : undefined} />
          <Field id="rp-again" label={t("auth.password_again")} type="password" autoComplete="new-password" required
            value={again} onChange={(e) => setAgain(e.target.value)}
            error={tried && mismatch ? t("auth.pw.mismatch") : undefined} />
          {reset.isError && <ErrorNote message={message(reset.error)} />}
          <Button type="submit" variant="primary" className="w-full" disabled={reset.isPending}>
            {t("auth.reset_button")}
          </Button>
        </form>
      )}
    </AuthCard>
  );
}
