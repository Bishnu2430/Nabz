import { useTranslation } from "react-i18next";

import type { Result } from "../../api/types";
import { formatUnit, formatValue } from "../../lib/format";
import { StatusIcon } from "./StatusMark";

/**
 * FR-17: a fixed, reviewed message shown before anything else when a value crosses a critical limit.
 * The wording comes from the translation bundle, never from a language model.
 */
export function CriticalBanner({ results }: { results: Result[] }) {
  const { t } = useTranslation();
  if (results.length === 0) return null;
  return (
    <section role="alert" aria-labelledby="critical-title"
      className="mb-8 rounded-lg border-2 border-critical bg-critical/5 p-5 text-ink">
      <div className="flex items-start gap-3">
        <span className="mt-1 text-critical"><StatusIcon status="critical_high" /></span>
        <div>
          <h2 id="critical-title" className="font-display text-2xl font-bold text-critical">{t("critical.title")}</h2>
          <p className="mt-2 max-w-prose">{t("critical.body")}</p>
          <p className="mt-4 text-sm font-medium text-muted">{t("critical.list")}</p>
          <ul className="mt-1 space-y-1">
            {results.map((r) => (
              <li key={r.observation_id} className="flex flex-wrap gap-x-2">
                <span className="font-medium">{r.test_name}</span>
                <span className="tabular">{formatValue(r.value, r.decimals)} {formatUnit(r.unit)}</span>
                <span className="text-critical">{t(`result_status.${r.status}`)}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
