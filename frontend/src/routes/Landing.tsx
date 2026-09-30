import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { useMe } from "../api/auth";
import { BodyDiagram } from "../components/body/BodyDiagram";

const STEPS = ["upload", "check", "understand"] as const;
const PROMISES = ["no_diagnosis", "your_check", "no_names", "delete"] as const;

/** The public front page (docs/12 §6): what Nabz does, how, and what it promises. */
export default function Landing() {
  const { t } = useTranslation();
  const me = useMe();
  const signedIn = Boolean(me.data);

  return (
    <div className="space-y-20 pb-8">
      <section className="grid items-center gap-10 md:grid-cols-[1.2fr_1fr]">
        <div>
          <h1 className="font-display text-4xl font-bold leading-tight sm:text-5xl">{t("app.tagline")}</h1>
          <p className="mt-5 max-w-prose text-lg text-muted">{t("landing.lead")}</p>
          <div className="mt-8 flex flex-wrap gap-3">
            {signedIn ? (
              <Link to="/home" className="rounded-md bg-accent px-5 py-2.5 font-medium text-accent-ink no-underline hover:brightness-110">
                {t("landing.open_family")}
              </Link>
            ) : (
              <>
                <Link to="/signup" className="rounded-md bg-accent px-5 py-2.5 font-medium text-accent-ink no-underline hover:brightness-110">
                  {t("auth.create_account")}
                </Link>
                <Link to="/login" className="rounded-md border border-hairline bg-raised px-5 py-2.5 font-medium no-underline hover:border-ink/40">
                  {t("auth.sign_in")}
                </Link>
              </>
            )}
          </div>
          <p className="mt-4 text-sm text-muted">{t("landing.languages")}</p>
        </div>
        <div className="mx-auto w-56 sm:w-64">
          <BodyDiagram decorative statuses={{ liver: "high", heart: "normal", kidney: "normal", blood: "normal", thyroid: "low" }} />
        </div>
      </section>

      <section aria-labelledby="how-h">
        <h2 id="how-h" className="font-display text-2xl font-bold">{t("landing.how_title")}</h2>
        <ol className="mt-6 grid gap-6 sm:grid-cols-3">
          {STEPS.map((step, i) => (
            <li key={step} className="border-t-2 border-ink/70 pt-4">
              <span className="font-display text-3xl text-accent" aria-hidden="true">{i + 1}</span>
              <h3 className="mt-1 text-lg font-semibold">{t(`landing.step_${step}`)}</h3>
              <p className="mt-1 text-muted">{t(`landing.step_${step}_body`)}</p>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="promise-h" className="rounded-lg border border-hairline bg-raised p-6 sm:p-8">
        <h2 id="promise-h" className="font-display text-2xl font-bold">{t("landing.promise_title")}</h2>
        <ul className="mt-4 grid gap-4 sm:grid-cols-2">
          {PROMISES.map((p) => (
            <li key={p} className="flex gap-3">
              <span aria-hidden="true" className="mt-2 size-2 shrink-0 rotate-45 bg-accent" />
              <span>{t(`landing.promise_${p}`)}</span>
            </li>
          ))}
        </ul>
        <p className="mt-6 flex flex-wrap gap-x-6 gap-y-2">
          <Link to="/privacy" className="text-link">{t("legal.privacy_title")}</Link>
          <Link to="/safety" className="text-link">{t("legal.safety_title")}</Link>
        </p>
      </section>
    </div>
  );
}
