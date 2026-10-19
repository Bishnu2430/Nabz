import clsx from "clsx";
import { useTranslation } from "react-i18next";

import type { Organ } from "../../api/types";
import { answerText } from "../../lib/format";
import { plainSummary, type PlainItem, type Tone } from "../../lib/plainSummary";
import { Icon, IconSeal, type IconName } from "../icons";
import { Card } from "../ui";

const ICON: Record<Tone, IconName> = { critical: "alert", out: "alert", ok: "check", info: "info" };
const COLOUR: Record<Tone, string> = {
  critical: "text-critical", out: "text-abnormal", ok: "text-normal", info: "text-muted",
};

/** "In short": what each result outside its range is and which way it is off, in plain words and no values. */
export function PlainSummary({ organs }: { organs: Organ[] }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  // English names are lower case inside a sentence; a sentence that starts with one capitalises it
  const first = (text: string) => (lang === "en" ? text.charAt(0).toUpperCase() + text.slice(1) : text);
  const join = (names: string[]) => names.length === 1 ? names[0]
    : `${names.slice(0, -1).join(t("plain.list_join"))}${t("plain.list_last")}${names[names.length - 1]}`;
  const areaName = (code: string) => t(`plain.area.${code}`, { defaultValue: t(`organs.${code}`) });
  const layName = (lay: string, fallback: string) => t(`lay.${lay}.name`, { defaultValue: fallback });

  const say = ({ lay, result, direction }: PlainItem): string => {
    const name = first(layName(lay, result.test_name));
    const role = t(`lay.${lay}.role`, { defaultValue: "" });
    if (result.answer) {
      return t(role ? "plain.say_word_role" : "plain.say_word", { Name: name, role,
        answer: answerText(result.answer), usual: answerText(result.usual ?? "absent") });
    }
    return t(role ? "plain.say_role" : "plain.say", { Name: name, role, dir: t(`plain.dir_${direction}`) });
  };

  const s = plainSummary(organs);
  const outAreas = s.areas.map((a) => a.code);

  return (
    <Card className="mb-6 px-5 py-4">
      <h2 className="mb-3 flex items-center gap-2.5 font-display text-xl font-bold">
        <IconSeal name="summary" />
        {t("plain.title")}
      </h2>
      <p className={clsx("mb-3 flex gap-2.5 text-[1.05rem] font-medium leading-relaxed",
        s.head === "critical" && "text-critical")}>
        <Icon name={s.head === "all_in" ? "check" : s.head === "no_ranges" ? "info" : "alert"} size={18}
          className={clsx("mt-1 shrink-0", s.head === "all_in" ? COLOUR.ok : s.head === "critical" ? COLOUR.critical
            : s.head === "no_ranges" ? COLOUR.info : COLOUR.out)} />
        <span>{t(`plain.head_${s.head}`)}</span>
      </p>

      {s.areas.length > 0 && (
        <ul className="space-y-3">
          {s.areas.map((a) => (
            <li key={a.code} className="flex gap-2.5 leading-relaxed">
              <Icon name={ICON[a.tone]} size={18} className={clsx("mt-1 shrink-0", COLOUR[a.tone])} />
              <div>
                <p className="font-semibold">{first(areaName(a.code))}</p>
                <ul className="mt-0.5 space-y-1">
                  {a.items.map((item) => <li key={item.lay}>{say(item)}</li>)}
                  {a.more && <li className="text-muted">{t("plain.more_here")}</li>}
                </ul>
              </div>
            </li>
          ))}
        </ul>
      )}

      <ul className="mt-3 space-y-2 leading-relaxed">
        {s.fine.length > 0 && s.head !== "all_in" && (
          <li className="flex gap-2.5">
            <Icon name="check" size={18} className={clsx("mt-1 shrink-0", COLOUR.ok)} />
            <span>{t("plain.areas_fine", { Areas: first(join(s.fine.map(areaName))) })}</span>
          </li>
        )}
        {s.changed.length > 0 && (
          <li className="flex gap-2.5">
            <Icon name="info" size={18} className={clsx("mt-1 shrink-0", COLOUR.info)} />
            <span>{t("plain.changed", { names: join(s.changed.map((l) => layName(l, l))) })}</span>
          </li>
        )}
        {s.trending.length > 0 && (
          <li className="flex gap-2.5">
            <Icon name="info" size={18} className={clsx("mt-1 shrink-0", COLOUR.info)} />
            <span>{t("plain.trending", { names: join(s.trending.map((l) => layName(l, l))) })}</span>
          </li>
        )}
        <li className="flex gap-2.5">
          <Icon name="info" size={18} className={clsx("mt-1 shrink-0", COLOUR.info)} />
          <span>
            {outAreas.length > 0
              ? `${t("plain.ask_about", { areas: join(outAreas.map(areaName)) })} ${t("plain.close_more")}`
              : t(s.head === "no_ranges" ? "plain.close_more" : "plain.close_all_in")}
          </span>
        </li>
      </ul>
      <p className="mt-3 text-sm text-muted">{t("plain.not_a_diagnosis")}</p>
    </Card>
  );
}
