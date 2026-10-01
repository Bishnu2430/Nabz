import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { useMe } from "../api/auth";
import { BodyDiagram } from "../components/body/BodyDiagram";
import { Reveal } from "../components/motion";

const STEPS = ["upload", "check", "understand"] as const;
const PROMISES = ["no_diagnosis", "your_check", "no_names", "delete"] as const;
const FEATURES = ["body", "exact", "trends", "languages", "records", "doctor"] as const;

/** The public front page (docs/12 §6): what Nabz does, how, and what it promises. */
export default function Landing() {
  const { t } = useTranslation();
  const me = useMe();
  const signedIn = Boolean(me.data);

  return (
    <div className="space-y-24 pb-8">
      <section className="grid items-center gap-10 md:grid-cols-[1.2fr_1fr]">
        <div className="stagger">
          <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-hairline bg-raised px-3 py-1 text-sm text-muted">
            <span aria-hidden="true" className="size-2 rounded-full bg-accent" />
            {t("landing.badge")}
          </p>
          <h1 className="font-display text-4xl font-bold leading-tight sm:text-5xl">
            {t("app.tagline")}
            {/* one brush stroke under the headline, drawn as the page opens */}
            <svg aria-hidden="true" viewBox="0 0 300 14" preserveAspectRatio="none" className="mt-2 block h-3 w-64 max-w-full text-accent">
              <path d="M4 9 C 60 2, 120 12, 180 6 S 270 5, 296 8" fill="none" stroke="currentColor" strokeWidth="4"
                strokeLinecap="round" pathLength={1} className="brush-underline" />
            </svg>
          </h1>
          <p className="mt-5 max-w-prose text-lg text-muted">{t("landing.lead")}</p>
          <div className="mt-8 flex flex-wrap gap-3">
            {signedIn ? (
              <Link to="/home" className="btn btn-primary rounded-md bg-accent px-5 py-2.5 font-medium text-accent-ink no-underline hover:brightness-110">
                {t("landing.open_family")}
              </Link>
            ) : (
              <>
                <Link to="/signup" className="btn btn-primary rounded-md bg-accent px-5 py-2.5 font-medium text-accent-ink no-underline hover:brightness-110">
                  {t("auth.create_account")}
                </Link>
                <Link to="/login" className="btn rounded-md border border-hairline bg-raised px-5 py-2.5 font-medium no-underline hover:border-ink/40">
                  {t("auth.sign_in")}
                </Link>
              </>
            )}
          </div>
          <p className="mt-4 text-sm text-muted">{t("landing.languages")}</p>
        </div>
        <div className="float mx-auto w-56 sm:w-64">
          <BodyDiagram decorative statuses={{ liver: "high", heart: "normal", kidney: "normal", blood: "normal", thyroid: "low" }} />
        </div>
      </section>

      <section aria-labelledby="how-h">
        <Reveal><h2 id="how-h" className="font-display text-2xl font-bold">{t("landing.how_title")}</h2></Reveal>
        <ol className="mt-6 grid gap-6 sm:grid-cols-3">
          {STEPS.map((step, i) => (
            <Reveal as="li" key={step} delay={i * 120} className="border-t-2 border-ink/70 pt-4">
              <span className="font-display text-3xl text-accent" aria-hidden="true">{i + 1}</span>
              <h3 className="mt-1 text-lg font-semibold">{t(`landing.step_${step}`)}</h3>
              <p className="mt-1 text-muted">{t(`landing.step_${step}_body`)}</p>
            </Reveal>
          ))}
        </ol>
      </section>

      <section aria-labelledby="what-h">
        <Reveal><h2 id="what-h" className="font-display text-2xl font-bold">{t("landing.features_title")}</h2></Reveal>
        <ul className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f, i) => (
            <Reveal as="li" key={f} delay={(i % 3) * 100}
              className="card lift rounded-lg border border-hairline bg-raised p-5">
              <FeatureIcon name={f} />
              <h3 className="mt-3 font-semibold">{t(`landing.feature_${f}`)}</h3>
              <p className="mt-1 text-sm text-muted">{t(`landing.feature_${f}_body`)}</p>
            </Reveal>
          ))}
        </ul>
      </section>

      <Reveal as="section" className="card rounded-lg border border-hairline bg-raised p-6 sm:p-8">
        <h2 id="promise-h" className="font-display text-2xl font-bold">{t("landing.promise_title")}</h2>
        <ul className="mt-4 grid gap-4 sm:grid-cols-2" aria-labelledby="promise-h">
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
      </Reveal>
    </div>
  );
}

function FeatureIcon({ name }: { name: (typeof FEATURES)[number] }) {
  const common = { width: 28, height: 28, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.6,
    strokeLinecap: "round" as const, strokeLinejoin: "round" as const, "aria-hidden": true, className: "text-accent" };
  switch (name) {
    case "body":
      return <svg {...common}><circle cx="12" cy="4.5" r="2.2" /><path d="M7 9h10M12 9v6M12 15l-3 6M12 15l3 6M7 9l-1.5 6M17 9l1.5 6" /></svg>;
    case "exact":
      return <svg {...common}><path d="M3 12h18M7 9v6M12 7v10M17 9v6" /></svg>;
    case "trends":
      return <svg {...common}><path d="M3 17l5-5 4 3 8-9" /><path d="M15 6h5v5" /></svg>;
    case "languages":
      return <svg {...common}><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3c3 3.5 3 14.5 0 18M12 3c-3 3.5-3 14.5 0 18" /></svg>;
    case "records":
      return <svg {...common}><rect x="3" y="3" width="18" height="18" rx="2" /><path d="M9 7.5a1.5 1.5 0 1 0-1 2.6L14 16a1.5 1.5 0 1 0 2.6-1L10.6 9A1.5 1.5 0 0 0 9 7.5Z" /></svg>;
    default:
      return <svg {...common}><path d="M6 3v6a4 4 0 0 0 8 0V3M10 13v3a5 5 0 0 0 10 0v-2" /><circle cx="20" cy="12" r="2" /></svg>;
  }
}
