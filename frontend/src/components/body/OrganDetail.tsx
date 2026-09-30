import { useTranslation } from "react-i18next";

import { useExplanation } from "../../api/hooks";
import type { Organ } from "../../api/types";
import { OrganCard } from "../insights/OrganCard";
import { isAbnormal } from "../insights/StatusMark";

/**
 * The card that opens when an organ system is chosen on the body map (FR-28): its values and trends, and the
 * first lines of the explanation for its results, taken from the explanation already on the page.
 */
export function OrganDetail({ organ, reportId, profileId }: { organ: Organ; reportId: string; profileId: string }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const explanation = useExplanation(reportId, lang).data?.explanation;
  const ordered = [...organ.results].sort((a, b) => Number(isAbnormal(b.status)) - Number(isAbnormal(a.status)));
  const excerpt = ordered
    .map((r) => explanation?.per_test.find((p) => p.test_code === r.test_code))
    .find((p) => p?.what_this_result_means);

  return (
    <div className="space-y-3">
      <OrganCard organ={organ} profileId={profileId} />
      {excerpt && (
        <blockquote className="border-l-2 border-accent pl-4">
          <p className="line-clamp-4">{excerpt.what_this_result_means}</p>
          <a href="#explanation" className="mt-1 inline-block text-sm text-link">{t("body.read_explanation")}</a>
        </blockquote>
      )}
    </div>
  );
}
