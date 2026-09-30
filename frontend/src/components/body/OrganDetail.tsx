import { useTranslation } from "react-i18next";

import { useExplanation } from "../../api/hooks";
import type { Organ } from "../../api/types";
import { isAbnormal } from "../insights/StatusMark";

/**
 * The first lines of the explanation for an organ system's results (the out-of-range ones first), taken from the
 * explanation already on the page. Shown in the organ panel (FR-28).
 */
export function ExplanationExcerpt({ organ, reportId }: { organ: Organ; reportId: string }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const explanation = useExplanation(reportId, lang).data?.explanation;
  const ordered = [...organ.results].sort((a, b) => Number(isAbnormal(b.status)) - Number(isAbnormal(a.status)));
  const excerpt = ordered
    .map((r) => explanation?.per_test.find((p) => p.test_code === r.test_code))
    .find((p) => p?.what_this_result_means);
  if (!excerpt) return null;
  return (
    <blockquote className="border-l-2 border-accent pl-4">
      <p className="line-clamp-4">{excerpt.what_this_result_means}</p>
      <a href="#explanation" className="mt-1 inline-block text-sm text-link">{t("body.read_explanation")}</a>
    </blockquote>
  );
}
