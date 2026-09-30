import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";

import { useMe, useVerifyEmail } from "../../api/auth";
import { AuthCard } from "../../components/AuthCard";
import { Button, ErrorNote, Notice } from "../../components/ui";
import { useAuthMessage } from "../../lib/account";

/**
 * Confirming takes a click rather than happening on load, so a mail scanner that opens links can't use up the
 * single-use token before the person does.
 */
export default function VerifyEmail() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const verify = useVerifyEmail();
  const me = useMe();
  const message = useAuthMessage();
  const onward = me.data ? { to: "/home", label: t("not_found.home") } : { to: "/login", label: t("auth.to_sign_in") };

  if (verify.isSuccess) {
    return (
      <AuthCard title={t("auth.verified_title")}>
        <Notice>{t("auth.verified_body")}</Notice>
        <Link to={onward.to} className="mt-6 inline-block text-link">{onward.label}</Link>
      </AuthCard>
    );
  }

  return (
    <AuthCard title={t("auth.verify_title")} intro={t("auth.verify_intro")}>
      {!token ? (
        <ErrorNote message={t("auth.err.token")} />
      ) : (
        <div className="space-y-4">
          {verify.isError && <ErrorNote message={message(verify.error)} />}
          <Button variant="primary" className="w-full" disabled={verify.isPending} onClick={() => verify.mutate(token)}>
            {t("auth.verify_button")}
          </Button>
        </div>
      )}
    </AuthCard>
  );
}
