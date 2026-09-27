import clsx from "clsx";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { useDeleteObservation, useEditObservation } from "../../api/hooks";
import type { Observation, ObservationPatch } from "../../api/types";
import { formatComputed, formatRange, formatUnit, position } from "../../lib/format";
import { AttentionMark, PositionMark } from "../Badges";
import { Button, ErrorNote, fieldClass } from "../ui";
import { TestPicker } from "./TestPicker";

/**
 * The number to show. When Nabz did not change it, the printed form is kept ("14.0" stays "14.0": the lab's
 * precision is information). When it was converted (4,803 /cumm -> 4.803 ×10³/µL), the canonical value is shown
 * and the printed one appears beside it so the person can check it against the page.
 */
export function displayValue(row: Pick<Observation, "value" | "raw_value">): { value: string; converted: boolean } {
  const raw = row.raw_value?.replace(/,/g, "").trim() ?? "";
  if (row.value == null) return { value: raw || "—", converted: false };
  if (raw && Number(raw) === Number(row.value)) return { value: raw, converted: false };
  return { value: formatComputed(row.value), converted: true };
}

export function ValueRow({ row, reportId, editable, active, onSelect }: {
  row: Observation;
  reportId: string;
  editable: boolean;
  active: boolean;
  onSelect: () => void;
}) {
  const { t } = useTranslation();
  const [editing, setEditing] = useState(false);
  const [confirmRemove, setConfirmRemove] = useState(false);
  const edit = useEditObservation(reportId);
  const remove = useDeleteObservation(reportId);

  const range = formatRange(row.ref_low, row.ref_high);
  const { value, converted } = displayValue(row);
  const unit = row.unit ? formatUnit(row.unit) : (row.raw_unit ?? "");
  const printed = `${row.raw_value ?? ""} ${row.raw_unit ?? ""}`.trim();

  const pick = (code: string) => edit.mutate({ id: row.id, patch: { test_code: code } });

  return (
    <li
      id={`row-${row.id}`}
      onMouseEnter={onSelect}
      onFocusCapture={onSelect}
      className={clsx(
        "scroll-mt-24 rounded-lg border p-4 transition",
        active ? "border-accent" : row.needs_attention ? "border-borderline/50" : "border-hairline",
        row.needs_attention ? "bg-borderline/5" : "bg-raised",
      )}
      title={`${t("review.confidence")}: ${Math.round(row.confidence * 100)}%`}
    >
      <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1">
        <div>
          <h3 className="font-medium">
            {row.test_name ?? <span className="text-borderline">{t("review.choose_test")}</span>}
          </h3>
          {row.raw_name && (
            <p className="text-sm text-muted">
              {t("review.printed")}: {row.raw_name}
              {row.edited && <span className="ml-2 rounded bg-sunken px-1.5 py-0.5 text-xs">{t("review.edited")}</span>}
            </p>
          )}
        </div>
        {row.needs_attention && <AttentionMark label={t("review.check")} />}
      </div>

      {!editing && (
        <>
          <div className="mt-3 flex flex-wrap items-baseline gap-x-4 gap-y-1">
            <p className="tabular text-2xl font-medium">
              {value} <span className="text-base font-normal text-muted">{unit}</span>
            </p>
            <PositionMark position={position(row.value, row.ref_low, row.ref_high)} />
          </div>
          <p className="mt-1 text-sm text-muted">
            {converted && <>{t("review.printed")}: <span className="tabular">{printed}</span> · </>}
            {range ? (
              <>
                <span className="tabular">{range}</span>{" "}
                ({row.ref_source === "report" ? t("review.from_report") : t("review.typical")})
              </>
            ) : (
              t("review.no_range")
            )}
          </p>
        </>
      )}

      {editable && !row.test_code && !editing && (
        <div className="mt-4 border-t border-hairline pt-4">
          <TestPicker value={null} candidates={row.candidates} onPick={pick} />
        </div>
      )}

      {editing && <EditForm row={row} reportId={reportId} onDone={() => setEditing(false)} />}

      {edit.isError && <div className="mt-3"><ErrorNote error={edit.error} /></div>}
      {remove.isError && <div className="mt-3"><ErrorNote error={remove.error} /></div>}

      {editable && !editing && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Button variant="quiet" className="px-0" onClick={() => setEditing(true)}>{t("review.edit")}</Button>
          <span aria-hidden="true" className="text-hairline">|</span>
          {confirmRemove ? (
            <>
              <span className="text-sm">{t("review.remove_confirm")}</span>
              <Button variant="danger" className="px-3 py-1 text-sm" disabled={remove.isPending}
                onClick={() => remove.mutate(row.id)}>
                {t("review.remove")}
              </Button>
              <Button className="px-3 py-1 text-sm" onClick={() => setConfirmRemove(false)}>{t("common.cancel")}</Button>
            </>
          ) : (
            <Button variant="quiet" className="px-0 text-abnormal" onClick={() => setConfirmRemove(true)}>
              {t("review.remove")}
            </Button>
          )}
        </div>
      )}
    </li>
  );
}

function EditForm({ row, reportId, onDone }: { row: Observation; reportId: string; onDone: () => void }) {
  const { t } = useTranslation();
  const edit = useEditObservation(reportId);
  const [rawValue, setRawValue] = useState(row.raw_value ?? "");
  const [rawUnit, setRawUnit] = useState(row.raw_unit ?? "");
  const [rawRange, setRawRange] = useState(row.raw_range ?? "");
  const [testCode, setTestCode] = useState(row.test_code);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const patch: ObservationPatch = {};
    if (rawValue !== (row.raw_value ?? "")) patch.raw_value = rawValue;
    if (rawUnit !== (row.raw_unit ?? "")) patch.raw_unit = rawUnit;
    if (rawRange !== (row.raw_range ?? "")) patch.raw_range = rawRange;
    if (testCode && testCode !== row.test_code) patch.test_code = testCode;
    if (Object.keys(patch).length === 0) return onDone();
    edit.mutate({ id: row.id, patch }, { onSuccess: onDone });
  };

  return (
    <form onSubmit={submit} className="mt-4 space-y-4 border-t border-hairline pt-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <Field label={t("review.value")} value={rawValue} onChange={setRawValue} inputMode="decimal" required />
        <Field label={t("review.unit")} value={rawUnit} onChange={setRawUnit} />
        <Field label={t("review.range")} value={rawRange} onChange={setRawRange} placeholder="13.0 - 17.0" />
      </div>
      <TestPicker value={testCode} candidates={row.candidates} onPick={setTestCode} />
      {edit.isError && <ErrorNote error={edit.error} />}
      <div className="flex gap-3">
        <Button type="submit" variant="primary" disabled={edit.isPending || !rawValue.trim()}>{t("common.save")}</Button>
        <Button onClick={onDone}>{t("common.cancel")}</Button>
      </div>
    </form>
  );
}

export function Field({ label, value, onChange, ...rest }: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  inputMode?: "decimal" | "text";
  placeholder?: string;
  required?: boolean;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm text-muted">{label}</span>
      <input value={value} onChange={(e) => onChange(e.target.value)} className={clsx(fieldClass, "tabular")} {...rest} />
    </label>
  );
}
