import { useTranslation } from "react-i18next";

import { Button, EmptyState } from "./ui";

/** Router error boundary: a render error shows this instead of a blank page. */
export function RouteError() {
  const { t } = useTranslation();
  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      <EmptyState
        title={t("route_error.title")}
        body={t("route_error.body")}
        action={<Button variant="primary" onClick={() => window.location.reload()}>{t("route_error.reload")}</Button>}
      />
    </main>
  );
}
