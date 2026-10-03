import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import { api, ApiError } from "../api/client";
import type { SharedReport } from "../api/types";
import { SharedReportView } from "../components/shared/SharedReportView";
import { Button, EmptyState, Loading } from "../components/ui";
import { formatDate } from "../lib/format";

/**
 * What a doctor sees from a share link (FR-34): one report, read-only, with no account. Results outside the
 * range first, each with its exact value, the lab's range and the change since the previous result.
 */
export default function Shared() {
  const { token = "" } = useParams();
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const shared = useQuery({
    queryKey: ["shared", token],
    queryFn: () => api.get<SharedReport>(`/v1/shared/${encodeURIComponent(token)}`),
    retry: false,
    staleTime: Infinity,
  });

  if (shared.isPending) return <Loading />;
  if (shared.isError) {
    const gone = shared.error instanceof ApiError && shared.error.status === 404;
    return <EmptyState title={gone ? t("shared.gone_title") : t("common.error")}
      body={gone ? t("shared.gone_body") : t("shared.try_later")} />;
  }
  const d = shared.data;

  return (
    <article className="mx-auto max-w-4xl">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-hairline bg-sunken px-4 py-3 text-sm print:hidden">
        <p>{t("shared.banner", { date: formatDate(d.expires_at, lang) })}</p>
        <Button onClick={() => window.print()}>{t("summary.print")}</Button>
      </div>

      <SharedReportView d={d} />
    </article>
  );
}
