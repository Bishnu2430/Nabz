import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { useForgotPassword } from "../../api/auth";
import { AuthCard } from "../../components/AuthCard";
import { Button, ErrorNote, Field, Notice } from "../../components/ui";
import { useAuthMessage } from "../../lib/account";
import { MailHint } from "./MailHint";

export default function ForgotPassword() {
  const { t } = useTranslation();
  const forgot = useForgotPassword();
  const message = useAuthMessage();
  const [email, setEmail] = useState("");

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (email.includes("@")) forgot.mutate(email.trim());
  };

  return (
    <AuthCard
      title={t("auth.forgot_title")}
      intro={forgot.isSuccess ? undefined : t("auth.forgot_intro")}
      footer={<p><Link to="/login" className="text-link">{t("auth.to_sign_in")}</Link></p>}
    >
      {forgot.isSuccess ? (
        <div className="space-y-4">
          {/* the same words whether or not the email has an account */}
          <Notice>{t("auth.forgot_sent")}</Notice>
          <MailHint />
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-4" noValidate>
          <Field id="fp-email" label={t("auth.email")} type="email" autoComplete="email" required value={email}
            onChange={(e) => setEmail(e.target.value)} />
          {forgot.isError && <ErrorNote message={message(forgot.error)} />}
          <Button type="submit" variant="primary" className="w-full" disabled={forgot.isPending || !email.includes("@")}>
            {t("auth.forgot_button")}
          </Button>
        </form>
      )}
    </AuthCard>
  );
}
