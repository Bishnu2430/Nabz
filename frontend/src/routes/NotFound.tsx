import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { EmptyState } from "../components/ui";

export default function NotFound() {
  const { t } = useTranslation();
  return (
    <EmptyState
      title={t("not_found.title")}
      body={t("not_found.body")}
      action={<Link to="/home" className="text-link">{t("not_found.home")}</Link>}
    />
  );
}
