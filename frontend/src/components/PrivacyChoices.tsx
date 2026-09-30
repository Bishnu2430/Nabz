import { useTranslation } from "react-i18next";

import { useConsents, useSetConsent } from "../api/hooks";
import type { ConsentPurpose } from "../api/types";
import { Card } from "./ui";

const SHOWN: ConsentPurpose[] = ["external_ai", "voice"];

/** Per-purpose consent toggles (FR-03). Withdrawing is as easy as giving. */
export function PrivacyChoices({ profileId }: { profileId: string }) {
  const { t } = useTranslation();
  const consents = useConsents(profileId);
  const set = useSetConsent(profileId);
  if (!consents.data) return null;
  const granted = Object.fromEntries(consents.data.map((c) => [c.purpose, c.granted]));

  return (
    <section aria-labelledby="privacy-h" className="mt-10">
      <h2 id="privacy-h" className="mb-3 font-display text-xl font-bold">{t("privacy.title")}</h2>
      <Card className="divide-y divide-hairline">
        {SHOWN.map((purpose) => (
          <label key={purpose} className="flex cursor-pointer items-start justify-between gap-4 px-5 py-4">
            <span>
              <span className="block font-medium">{t(`privacy.${purpose}`)}</span>
              <span className="block text-sm text-muted">{t(`privacy.${purpose}_note`)}</span>
            </span>
            <span className="flex shrink-0 items-center gap-2 text-sm">
              <span className="text-muted">{granted[purpose] ? t("privacy.on") : t("privacy.off")}</span>
              <input type="checkbox" role="switch" checked={Boolean(granted[purpose])} disabled={set.isPending}
                onChange={(e) => set.mutate({ purpose, granted: e.target.checked })}
                className="size-5 accent-[var(--accent)]" />
            </span>
          </label>
        ))}
      </Card>
    </section>
  );
}
