import clsx from "clsx";
import { useState, type FormEvent, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import {
  useAdminCatalogue, useCatalogueTest, useEditCatalogue, type CatalogueTest, type Conversion, type CriticalLimit, type RangeRow,
} from "../../api/catalogue";
import type { Sex } from "../../api/types";
import { Icon } from "../../components/icons";
import { Modal } from "../../components/Modal";
import { useToast } from "../../components/Toast";
import { Button, ErrorNote, Loading, fieldClass } from "../../components/ui";
import { formatDate, formatDateTime } from "../../lib/format";

const SEXES: Sex[] = ["unknown", "female", "male"];
const small = clsx(fieldClass, "py-1 text-sm");

/** The critical limits of a test as "low – high unit", with "—" for a side that has none. */
function limitText(low: string | null, high: string | null, unit: string) {
  return `${low ?? "—"} – ${high ?? "—"} ${unit}`;
}

/** Whether a clinical reviewer has signed the limit off, or a change is waiting for one. */
export function LimitState({ limit }: { limit: CriticalLimit }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const [tone, icon, text] = limit.proposed
    ? ["text-borderline", "clock", t("catalogue.limit_proposed")] as const
    : limit.reviewed_at
      ? ["text-normal", "check", t("catalogue.limit_signed", { who: limit.reviewed_by, date: formatDate(limit.reviewed_at, lang) })] as const
      : ["text-borderline", "info", t("catalogue.limit_unreviewed")] as const;
  return <span className={clsx("inline-flex items-center gap-1 text-xs", tone)}><Icon name={icon} size={12} />{text}</span>;
}

/**
 * The tests Nabz knows (FR-35): names and aliases the reader matches, units it converts, default ranges for reports
 * that print none, and critical limits, which a clinical reviewer has to approve before they apply.
 */
export function CatalogueTab() {
  const { t } = useTranslation();
  const [q, setQ] = useState("");
  const [open, setOpen] = useState<string | null>(null);
  const tests = useAdminCatalogue(q.trim());
  return (
    <section>
      <label className="mb-4 block max-w-sm">
        <span className="sr-only">{t("catalogue.search")}</span>
        <input type="search" value={q} onChange={(e) => setQ(e.target.value)} className={fieldClass} placeholder={t("catalogue.search")} />
      </label>
      {tests.isPending && <Loading />}
      {tests.isError && <ErrorNote error={tests.error} />}
      {tests.data && (
        <div className="overflow-x-auto rounded-lg border border-hairline bg-raised">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-hairline text-muted">
              <tr>{["test", "organ", "unit", "aliases", "ranges", "critical"].map((c) => (
                <th key={c} className="px-3 py-2 font-medium">{t(`catalogue.c_${c}`)}</th>
              ))}</tr>
            </thead>
            <tbody className="divide-y divide-hairline">
              {tests.data.map((r) => (
                <tr key={r.code} className="hover:bg-sunken/60">
                  <td className="px-3 py-2">
                    <button type="button" className="text-left font-medium text-link hover:underline" onClick={() => setOpen(r.code)}>
                      {r.name}
                    </button>
                    <span className="block text-xs text-muted">{r.short_name} · {r.code}</span>
                  </td>
                  <td className="px-3 py-2">{t(`organs.${r.organ}`, r.organ)}</td>
                  <td className="px-3 py-2">{r.unit}</td>
                  <td className="tabular px-3 py-2">{r.aliases}</td>
                  <td className="tabular px-3 py-2">{r.ranges}</td>
                  <td className="px-3 py-2">
                    {r.critical ? (
                      <>
                        <span className="tabular block">{limitText(r.critical.low, r.critical.high, r.unit)}</span>
                        <LimitState limit={r.critical} />
                      </>
                    ) : <span className="text-muted">—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="mt-3 max-w-prose text-sm text-muted">{t("catalogue.note")}</p>
      {open && <TestEditor code={open} onClose={() => setOpen(null)} />}
    </section>
  );
}

function Part({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <section className="border-t border-hairline pt-4 first:border-t-0 first:pt-0">
      <h3 className="font-medium">{title}</h3>
      {hint && <p className="mb-2 text-sm text-muted">{hint}</p>}
      <div className={hint ? "" : "mt-2"}>{children}</div>
    </section>
  );
}

function TestEditor({ code, onClose }: { code: string; onClose: () => void }) {
  const { t } = useTranslation();
  const test = useCatalogueTest(code);
  return (
    <Modal title={test.data ? test.data.name : t("common.loading")} onClose={onClose} wide>
      {test.isPending && <Loading />}
      {test.isError && <ErrorNote error={test.error} />}
      {test.data && <Editor key={test.data.history[0]?.at ?? "none"} test={test.data} />}
    </Modal>
  );
}

function Editor({ test }: { test: CatalogueTest }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const edit = useEditCatalogue(test.code);
  const toast = useToast();
  const saved = () => toast(t("catalogue.saved"));

  const [names, setNames] = useState({ name: test.name, short_name: test.short_name, decimals: String(test.decimals),
    plausible_min: test.plausible_min, plausible_max: test.plausible_max });
  const [aliases, setAliases] = useState(test.aliases.join("\n"));
  const [units, setUnits] = useState<Conversion[]>(test.conversions);
  const [ranges, setRanges] = useState<RangeRow[]>(test.ranges);
  const [limit, setLimit] = useState({ low: test.critical?.low ?? "", high: test.critical?.high ?? "", note: "" });

  const submit = (e: FormEvent, change: Parameters<typeof edit.mutate>[0]) => {
    e.preventDefault();
    edit.mutate(change, { onSuccess: saved });
  };
  const blank = (v: string) => (v.trim() === "" ? null : v.trim());

  return (
    <div className="space-y-5">
      <p className="text-sm text-muted">{[test.code, `LOINC ${test.loinc}`, test.panel, test.unit].join(" · ")}</p>
      {edit.isError && <ErrorNote error={edit.error} />}

      <Part title={t("catalogue.p_names")}>
        <form className="grid gap-3 sm:grid-cols-2" onSubmit={(e) => submit(e, { kind: "test", body: {
          name: names.name, short_name: names.short_name, decimals: Number(names.decimals),
          plausible_min: names.plausible_min, plausible_max: names.plausible_max } })}>
          {(["name", "short_name", "decimals", "plausible_min", "plausible_max"] as const).map((f) => (
            <label key={f} className="text-sm">
              <span className="mb-1 block font-medium">{t(`catalogue.f_${f}`, { unit: test.unit })}</span>
              <input value={names[f]} required inputMode={f === "name" || f === "short_name" ? undefined : "decimal"}
                onChange={(e) => setNames({ ...names, [f]: e.target.value })} className={small} />
            </label>
          ))}
          <div className="self-end"><Button type="submit" disabled={edit.isPending}>{t("catalogue.save")}</Button></div>
        </form>
      </Part>

      <Part title={t("catalogue.p_aliases")} hint={t("catalogue.aliases_hint")}>
        <form onSubmit={(e) => submit(e, { kind: "test", body: { aliases: aliases.split("\n").map((a) => a.trim()).filter(Boolean) } })}>
          <textarea value={aliases} onChange={(e) => setAliases(e.target.value)} rows={5} aria-label={t("catalogue.p_aliases")}
            className={clsx(fieldClass, "font-mono text-sm")} />
          <Button type="submit" className="mt-2" disabled={edit.isPending}>{t("catalogue.save")}</Button>
        </form>
      </Part>

      <Part title={t("catalogue.p_units")} hint={t("catalogue.units_hint", { unit: test.unit })}>
        <form onSubmit={(e) => submit(e, { kind: "conversions", body: units })}>
          <RowsTable head={[t("catalogue.f_from_unit"), t("catalogue.f_factor"), t("catalogue.f_offset")]}
            rows={units} onRemove={(i) => setUnits(units.filter((_, j) => j !== i))}
            render={(u, i) => (["from_unit", "factor", "offset"] as const).map((f) => (
              <input key={f} value={u[f]} required aria-label={`${t(`catalogue.f_${f}`)} ${i + 1}`} className={small}
                onChange={(e) => setUnits(units.map((x, j) => (j === i ? { ...x, [f]: e.target.value } : x)))} />
            ))} />
          <div className="mt-2 flex gap-2">
            <Button type="button" variant="quiet" onClick={() => setUnits([...units, { from_unit: "", factor: "1", offset: "0" }])}>
              {t("catalogue.add_row")}
            </Button>
            <Button type="submit" disabled={edit.isPending}>{t("catalogue.save")}</Button>
          </div>
        </form>
      </Part>

      <Part title={t("catalogue.p_ranges")} hint={t("catalogue.ranges_hint")}>
        <form onSubmit={(e) => submit(e, { kind: "ranges", body: ranges.map((r) => ({ ...r, low: blank(r.low ?? ""), high: blank(r.high ?? "") })) })}>
          <RowsTable head={[t("catalogue.f_sex"), t("catalogue.f_age_min"), t("catalogue.f_age_max"), t("catalogue.f_low", { unit: test.unit }),
            t("catalogue.f_high", { unit: test.unit })]}
            rows={ranges} onRemove={(i) => setRanges(ranges.filter((_, j) => j !== i))}
            render={(r, i) => {
              const set = (patch: Partial<RangeRow>) => setRanges(ranges.map((x, j) => (j === i ? { ...x, ...patch } : x)));
              return [
                <select key="sex" value={r.sex} onChange={(e) => set({ sex: e.target.value as Sex })} className={small}
                  aria-label={`${t("catalogue.f_sex")} ${i + 1}`}>
                  {SEXES.map((s) => <option key={s} value={s}>{t(`catalogue.sex_${s}`)}</option>)}
                </select>,
                <input key="amin" type="number" min={0} max={120} value={r.age_min} className={small} aria-label={`${t("catalogue.f_age_min")} ${i + 1}`}
                  onChange={(e) => set({ age_min: Number(e.target.value) })} />,
                <input key="amax" type="number" min={0} max={120} value={r.age_max} className={small} aria-label={`${t("catalogue.f_age_max")} ${i + 1}`}
                  onChange={(e) => set({ age_max: Number(e.target.value) })} />,
                <input key="low" value={r.low ?? ""} inputMode="decimal" className={small} aria-label={`${t("catalogue.f_low", { unit: test.unit })} ${i + 1}`}
                  onChange={(e) => set({ low: e.target.value })} />,
                <input key="high" value={r.high ?? ""} inputMode="decimal" className={small} aria-label={`${t("catalogue.f_high", { unit: test.unit })} ${i + 1}`}
                  onChange={(e) => set({ high: e.target.value })} />,
              ];
            }} />
          <div className="mt-2 flex gap-2">
            <Button type="button" variant="quiet"
              onClick={() => setRanges([...ranges, { sex: "unknown", age_min: 18, age_max: 120, low: "", high: "" }])}>
              {t("catalogue.add_row")}
            </Button>
            <Button type="submit" disabled={edit.isPending}>{t("catalogue.save")}</Button>
          </div>
        </form>
      </Part>

      <Part title={t("catalogue.p_critical")} hint={t("catalogue.critical_hint")}>
        {test.critical && (
          <div className="mb-3 rounded-md border border-hairline bg-sunken px-3 py-2 text-sm">
            <p><span className="text-muted">{t("catalogue.limit_now")}:</span>{" "}
              <span className="tabular font-medium">{limitText(test.critical.low, test.critical.high, test.unit)}</span></p>
            <LimitState limit={test.critical} />
            {test.critical.proposed && (
              <p className="mt-1">
                {t("catalogue.limit_waiting", { limits: limitText(test.critical.proposed.low, test.critical.proposed.high, test.unit),
                  who: test.critical.proposed.by ?? "—", date: formatDate(test.critical.proposed.at, lang) })}
                {test.critical.proposed.note && <> — “{test.critical.proposed.note}”</>}
              </p>
            )}
          </div>
        )}
        <form className="grid gap-3 sm:grid-cols-[1fr_1fr_2fr_auto] sm:items-end"
          onSubmit={(e) => submit(e, { kind: "limit", body: { low: blank(limit.low), high: blank(limit.high), note: limit.note } })}>
          {(["low", "high"] as const).map((f) => (
            <label key={f} className="text-sm">
              <span className="mb-1 block font-medium">{t(`catalogue.f_critical_${f}`, { unit: test.unit })}</span>
              <input value={limit[f]} inputMode="decimal" onChange={(e) => setLimit({ ...limit, [f]: e.target.value })} className={small} />
            </label>
          ))}
          <label className="text-sm">
            <span className="mb-1 block font-medium">{t("catalogue.f_reason")}</span>
            <input value={limit.note} required minLength={3} maxLength={500} onChange={(e) => setLimit({ ...limit, note: e.target.value })}
              className={small} />
          </label>
          <Button type="submit" disabled={edit.isPending}>{t("catalogue.propose")}</Button>
        </form>
      </Part>

      <Part title={t("catalogue.p_history")}>
        {test.history.length === 0 ? <p className="text-sm text-muted">{t("catalogue.no_history")}</p> : (
          <ul className="space-y-1 text-sm">
            {test.history.map((h, i) => (
              <li key={i} className="flex flex-wrap gap-x-3">
                <span className="tabular text-muted">{formatDateTime(h.at, lang)}</span>
                <span className="font-medium">{t(`catalogue.a_${h.action.split(".")[1]}`, h.action)}</span>
                <span className="text-muted">{h.actor ?? "—"}</span>
              </li>
            ))}
          </ul>
        )}
      </Part>
    </div>
  );
}

function RowsTable<T>({ head, rows, render, onRemove }: {
  head: string[];
  rows: T[];
  render: (row: T, i: number) => ReactNode[];
  onRemove: (i: number) => void;
}) {
  const { t } = useTranslation();
  if (rows.length === 0) return <p className="text-sm text-muted">{t("catalogue.none")}</p>;
  return (
    <table className="w-full text-sm">
      <thead className="text-left text-muted">
        <tr>{head.map((h) => <th key={h} className="pb-1 pr-2 font-medium">{h}</th>)}<th /></tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr key={i}>
            {render(row, i).map((cell, j) => <td key={j} className="py-1 pr-2">{cell}</td>)}
            <td className="py-1">
              <button type="button" onClick={() => onRemove(i)} className="text-abnormal hover:underline"
                aria-label={t("catalogue.remove_row", { n: i + 1 })}>
                <Icon name="trash" size={16} />
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
