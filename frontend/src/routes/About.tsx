import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { IconSeal, type IconName } from "../components/icons";
import { Card } from "../components/ui";

/** What Nabz draws on, what each is used for and under what licence (data/external.md, data/imaging/README.md). */
const SOURCES: { id: string; icon: IconName; name: string; url: string; licence: string }[] = [
  { id: "medlineplus", icon: "book", name: "MedlinePlus, U.S. National Library of Medicine", url: "https://medlineplus.gov/",
    licence: "Public domain (NLM-authored pages only; licensed A.D.A.M. content is excluded)" },
  { id: "nhanes", icon: "trend", name: "NHANES 2017–March 2020, CDC National Center for Health Statistics",
    url: "https://wwwn.cdc.gov/nchs/nhanes/", licence: "Public domain" },
  { id: "loinc", icon: "tests", name: "LOINC®, Regenstrief Institute", url: "https://loinc.org/", licence: "LOINC licence (see the notice below)" },
  { id: "e5", icon: "search", name: "multilingual-e5-small (intfloat), int8 ONNX export by Xenova",
    url: "https://huggingface.co/intfloat/multilingual-e5-small", licence: "MIT" },
  { id: "gptoss", icon: "pen", name: "gpt-oss-120b (OpenAI), served by Groq", url: "https://groq.com/", licence: "Apache 2.0 (model weights)" },
  { id: "elevenlabs", icon: "play", name: "ElevenLabs", url: "https://elevenlabs.io/", licence: "Commercial service" },
  { id: "ocr", icon: "eye", name: "RapidOCR on ONNX Runtime; PDFium through pypdfium2; OpenCV",
    url: "https://github.com/RapidAI/RapidOCR", licence: "Apache 2.0; MIT; BSD-3-Clause and Apache 2.0; Apache 2.0" },
  { id: "fonts", icon: "globe", name: "Noto Sans, Noto Sans Devanagari, Noto Sans Oriya, Shippori Mincho",
    url: "https://fonts.google.com/", licence: "SIL Open Font License 1.1" },
];

const IMAGES = [
  { what: "chest_normal", author: "Mikael Häggström, M.D.", licence: "CC0 1.0",
    url: "https://commons.wikimedia.org/wiki/File:Normal_posteroanterior_(PA)_chest_radiograph_(X-ray).jpg" },
  { what: "chest_consolidation", author: "Malvinder S Parmar (BMC Infectious Diseases 2005, 5:30)", licence: "CC BY 2.0",
    url: "https://commons.wikimedia.org/wiki/File:X-ray_lung_consolidation.jpg" },
  { what: "knee_xray", author: "James Heilman, MD", licence: "CC BY-SA 4.0",
    url: "https://commons.wikimedia.org/wiki/File:Osteoarthritis_on_X-ray.jpg" },
  { what: "lumbar_mri", author: "Stillwaterising", licence: "CC0 1.0",
    url: "https://commons.wikimedia.org/wiki/File:Lumbar_MRI_t2-tse-rst-sagittal_07.jpg" },
  { what: "knee_mri", author: "Pil Kang (Walter Reed Army Medical Center)", licence: "Public domain",
    url: "https://commons.wikimedia.org/wiki/File:OCD_WalterReed_MRI-Sagital-T2.jpeg" },
];

const SOFTWARE = [
  ["React, React Router, TanStack Query, i18next, three.js, React Three Fiber, drei, clsx", "MIT"],
  ["FastAPI, SQLAlchemy, Alembic, Pydantic, pgvector-python, RapidFuzz, argon2-cffi, PyOTP", "MIT"],
  ["Uvicorn, Segno", "BSD-3-Clause"],
  ["Hugging Face Tokenizers, python-multipart, cryptography", "Apache 2.0"],
  ["Pillow", "MIT-CMU"],
  ["psycopg", "LGPL-3.0"],
  ["PostgreSQL, pgvector", "PostgreSQL License"],
];

/** About Nabz: what it does in a paragraph, and every source, model, font and library it uses with its licence. */
export default function About() {
  const { t } = useTranslation();
  return (
    <article className="mx-auto max-w-3xl">
      <div className="page-head flex items-center gap-4">
        <IconSeal name="info" size={24} className="icon-seal-lg" />
        <h1 className="font-display text-3xl font-bold sm:text-4xl">{t("about.title")}</h1>
      </div>
      <p className="mt-3 text-lg text-muted">{t("about.intro")}</p>

      <section className="mt-8">
        <h2 className="font-display text-xl font-bold">{t("about.how_h")}</h2>
        <ol className="mt-2 list-decimal space-y-1 pl-5">
          {(["read", "confirm", "analyse", "explain", "share"] as const).map((s) => <li key={s}>{t(`about.how_${s}`)}</li>)}
        </ol>
        <p className="mt-3 text-sm">
          <Link to="/safety" className="text-link">{t("legal.safety_title")}</Link> · <Link to="/privacy" className="text-link">{t("legal.privacy_title")}</Link>
          {" "}· <Link to="/help" className="text-link">{t("help.title")}</Link>
        </p>
      </section>

      <section className="mt-10" aria-labelledby="about-sources">
        <h2 id="about-sources" className="font-display text-xl font-bold">{t("about.sources_h")}</h2>
        <p className="mt-1 text-muted">{t("about.sources_intro")}</p>
        <ul className="stagger mt-4 space-y-3">
          {SOURCES.map((s) => (
            <li key={s.id}>
              <Card className="flex items-start gap-3 px-4 py-3">
                <IconSeal name={s.icon} />
                <div className="min-w-0">
                  <a href={s.url} target="_blank" rel="noreferrer" className="font-medium text-link">{s.name} ↗</a>
                  <p className="text-sm">{t(`about.use_${s.id}`)}</p>
                  <p className="text-sm text-muted">{t("about.licence", { licence: s.licence })}</p>
                </div>
              </Card>
            </li>
          ))}
        </ul>
        <p className="mt-4 rounded-md border border-hairline bg-sunken px-4 py-3 text-sm">
          This material contains content from LOINC® (<a href="https://loinc.org" className="text-link">https://loinc.org</a>). LOINC is
          copyright © Regenstrief Institute, Inc. and the Logical Observation Identifiers Names and Codes (LOINC) Committee and is
          available at no cost under the license at <a href="https://loinc.org/license" className="text-link">https://loinc.org/license</a>.
          LOINC® is a registered United States trademark of Regenstrief Institute, Inc.
        </p>
      </section>

      <section className="mt-10" aria-labelledby="about-images">
        <h2 id="about-images" className="font-display text-xl font-bold">{t("about.images_h")}</h2>
        <p className="mt-1 text-muted">{t("about.images_intro")}</p>
        <ul className="mt-3 divide-y divide-hairline text-sm">
          {IMAGES.map((i) => (
            <li key={i.what} className="py-2">
              <a href={i.url} target="_blank" rel="noreferrer" className="font-medium text-link">{t(`about.image_${i.what}`)} ↗</a>
              <span className="text-muted"> · {i.author} · {i.licence}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-10" aria-labelledby="about-software">
        <h2 id="about-software" className="font-display text-xl font-bold">{t("about.software_h")}</h2>
        <p className="mt-1 text-muted">{t("about.software_intro")}</p>
        <table className="mt-3 w-full text-left text-sm">
          <tbody className="divide-y divide-hairline">
            {SOFTWARE.map(([names, licence]) => (
              <tr key={names}><td className="py-2 pr-4">{names}</td><td className="whitespace-nowrap py-2 text-muted">{licence}</td></tr>
            ))}
          </tbody>
        </table>
      </section>
      <p className="mt-10 text-sm text-muted">{t("about.fictional")}</p>
    </article>
  );
}
