import clsx from "clsx";
import { useId, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { useCatalogue } from "../../api/hooks";
import { formatUnit } from "../../lib/format";
import { fieldClass } from "../ui";

const squash = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, "");

/** Suggestions from the matcher first, then a search over the whole catalogue. */
export function TestPicker({ value, candidates, onPick }: {
  value: string | null;
  candidates: [string, string, number][];
  onPick: (code: string) => void;
}) {
  const { t } = useTranslation();
  const catalogue = useCatalogue();
  const [query, setQuery] = useState("");
  const inputId = useId();

  const results = useMemo(() => {
    const q = squash(query);
    if (!q || !catalogue.data) return [];
    return catalogue.data
      .filter((c) => [c.name, c.short_name, c.code].some((s) => squash(s).includes(q)))
      .slice(0, 8);
  }, [query, catalogue.data]);

  const selectedName = catalogue.data?.find((c) => c.code === value)?.name;

  return (
    <div className="space-y-3">
      {selectedName && (
        <p className="text-sm">
          <span className="text-muted">{t("review.test")}: </span>
          <span className="font-medium">{selectedName}</span>
        </p>
      )}
      {candidates.length > 0 && (
        <div>
          <p className="mb-1.5 text-sm text-muted">{t("review.suggestions")}</p>
          <div className="flex flex-wrap gap-2">
            {candidates.map(([code, name]) => (
              <button
                key={code}
                type="button"
                onClick={() => onPick(code)}
                aria-pressed={code === value}
                className={clsx(
                  "rounded-full border px-3 py-1 text-sm",
                  code === value ? "border-ink bg-sunken font-medium" : "border-hairline bg-raised hover:border-ink/40",
                )}
              >
                {name}
              </button>
            ))}
          </div>
        </div>
      )}
      <div>
        <label htmlFor={inputId} className="mb-1 block text-sm text-muted">{t("review.search_tests")}</label>
        <input
          id={inputId}
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t("review.search_placeholder")}
          className={fieldClass}
          autoComplete="off"
        />
        {results.length > 0 && (
          <ul className="mt-1 divide-y divide-hairline rounded-md border border-hairline bg-raised" aria-label={t("review.search_tests")}>
            {results.map((c) => (
              <li key={c.code}>
                <button
                  type="button"
                  onClick={() => { onPick(c.code); setQuery(""); }}
                  className="flex w-full items-baseline justify-between gap-3 px-3 py-2 text-left hover:bg-sunken"
                >
                  <span>{c.name}</span>
                  <span className="text-sm text-muted">{formatUnit(c.unit)}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
