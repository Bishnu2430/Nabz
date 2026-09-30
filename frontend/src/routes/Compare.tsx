import clsx from "clsx";
import { useTranslation } from "react-i18next";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { useBodyMap, useProfiles } from "../api/hooks";
import type { ResultBrief } from "../api/types";
import { ORGAN_ORDER } from "../components/body/organs";
import { StatusIcon, isAbnormal } from "../components/insights/StatusMark";
import { Card, ErrorNote, fieldClass, Loading, PageTitle } from "../components/ui";
import { formatDate, formatPercent, formatRange, formatUnit, formatValue } from "../lib/format";
import { frameResults } from "../lib/series";

/** Two reports side by side: every test in either, both values, the change and what moved in or out of range. */
export default function Compare() {
  const { id = "" } = useParams();
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const profile = useProfiles().data?.find((p) => p.id === id);
  const frames = useBodyMap(id);
  const [params, setParams] = useSearchParams();

  if (frames.isPending) return <Loading />;
  if (frames.isError) return <ErrorNote error={frames.error} />;
  const list = frames.data;
  if (list.length < 2) {
    return (
      <>
        <Link to={`/p/${id}`} className="text-link">← {profile?.display_name}</Link>
        <PageTitle title={t("compare.title")} subtitle={t("compare.need_two")} />
      </>
    );
  }
  const aId = params.get("a") ?? list[list.length - 2].report_id;
  const bId = params.get("b") ?? list[list.length - 1].report_id;
  const a = list.find((f) => f.report_id === aId) ?? list[list.length - 2];
  const b = list.find((f) => f.report_id === bId) ?? list[list.length - 1];
  const ra = frameResults(a);
  const rb = frameResults(b);
  const organOf = new Map<string, string>();
  for (const f of [a, b]) for (const o of f.organs) for (const r of o.tests) organOf.set(r.test_code, o.code);
  const codes = [...new Set([...ra.keys(), ...rb.keys()])];
  const pick = (key: "a" | "b", value: string) => setParams((p) => { p.set(key, value); return p; }, { replace: true });
  const label = (f: typeof a) => `${formatDate(f.date, lang)}${f.lab_name ? ` · ${f.lab_name}` : ""}`;
  const changed = codes.filter((c) => {
    const x = ra.get(c);
    const y = rb.get(c);
    return x && y && isAbnormal(x.status) !== isAbnormal(y.status);
  }).length;

  return (
    <>
      <Link to={`/p/${id}`} className="text-link">← {profile?.display_name}</Link>
      <PageTitle title={t("compare.title")} subtitle={t("compare.subtitle", { count: changed })} />
      <div className="mb-6 grid gap-4 sm:grid-cols-2">
        {(["a", "b"] as const).map((key) => (
          <label key={key}>
            <span className="mb-1 block font-medium">{t(`compare.${key}`)}</span>
            <select value={key === "a" ? a.report_id : b.report_id} onChange={(e) => pick(key, e.target.value)}
              className={fieldClass}>
              {list.map((f) => <option key={f.report_id} value={f.report_id}>{label(f)}</option>)}
            </select>
          </label>
        ))}
      </div>
      {ORGAN_ORDER.map((organ) => {
        const rows = codes.filter((c) => organOf.get(c) === organ);
        if (rows.length === 0) return null;
        return (
          <section key={organ} className="mb-6">
            <h2 className="mb-2 font-display text-xl font-bold">{t(`organs.${organ}`)}</h2>
            <Card className="overflow-x-auto">
              <table className="w-full min-w-[36rem] text-left">
                <thead className="text-sm text-muted">
                  <tr className="border-b border-hairline">
                    <th className="px-4 py-2 font-medium">{t("compare.test")}</th>
                    <th className="px-4 py-2 font-medium">{formatDate(a.date, lang)}</th>
                    <th className="px-4 py-2 font-medium">{formatDate(b.date, lang)}</th>
                    <th className="px-4 py-2 font-medium">{t("compare.change")}</th>
                    <th className="px-4 py-2 font-medium">{t("compare.range")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-hairline">
                  {rows.map((c) => <CompareRow key={c} x={ra.get(c)} y={rb.get(c)} profileId={id} />)}
                </tbody>
              </table>
            </Card>
          </section>
        );
      })}
    </>
  );
}

function Cell({ r }: { r?: ResultBrief }) {
  if (!r) return <td className="px-4 py-2 text-muted">—</td>;
  const out = isAbnormal(r.status);
  return (
    <td className={clsx("tabular px-4 py-2", out ? "font-medium text-abnormal" : "")}>
      <span className="inline-flex items-center gap-1">
        {out && <StatusIcon status={r.status} />}
        {formatValue(r.value, r.decimals)} <span className="text-sm font-normal text-muted">{formatUnit(r.unit)}</span>
      </span>
    </td>
  );
}

function CompareRow({ x, y, profileId }: { x?: ResultBrief; y?: ResultBrief; profileId: string }) {
  const { t } = useTranslation();
  const r = (y ?? x)!;
  const fraction = x && y && Number(x.value) ? Number(y.value) / Number(x.value) - 1 : null;
  const movedIn = x && y && isAbnormal(x.status) && !isAbnormal(y.status);
  const movedOut = x && y && !isAbnormal(x.status) && isAbnormal(y.status);
  return (
    <tr>
      <td className="px-4 py-2">
        <Link to={`/p/${profileId}/tests/${r.test_code}`} className="text-ink hover:text-link">{r.test_name}</Link>
      </td>
      <Cell r={x} />
      <Cell r={y} />
      <td className="tabular px-4 py-2 text-sm">
        {fraction != null ? formatPercent(fraction) : "—"}
        {movedIn && <span className="ml-2 text-normal">{t("compare.back_in")}</span>}
        {movedOut && <span className="ml-2 text-abnormal">{t("compare.went_out")}</span>}
      </td>
      <td className="tabular px-4 py-2 text-sm text-muted">{formatRange(r.ref_low, r.ref_high)}</td>
    </tr>
  );
}
