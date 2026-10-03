import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { useAdminCatalogue, useKnowledge, useKnowledgeAction, type KbDocumentIn } from "../../api/catalogue";
import { Icon } from "../../components/icons";
import { Light, StatTile } from "../../components/staff/parts";
import { useToast } from "../../components/Toast";
import { Button, Card, ErrorNote, Loading, SectionTitle, fieldClass } from "../../components/ui";
import { formatDate } from "../../lib/format";

const LICENCES = ["Public domain (U.S. government work)", "CC BY 4.0", "CC BY-SA 4.0", "CC0 1.0"];
const EMPTY: KbDocumentIn = { title: "", source_org: "", url: "", license: LICENCES[0], language: "en", test_code: "", text: "" };

/**
 * The passages explanations and answers quote (FR-36): where each came from and under what licence, which tests they
 * are about and how often they have been cited. Adding a document embeds it at once; re-embedding is for a new model.
 */
export function KnowledgeTab() {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const kb = useKnowledge();
  const act = useKnowledgeAction();
  const toast = useToast();
  const [adding, setAdding] = useState(false);
  const reembed = (id?: string) => act.mutate({ kind: "reembed", id }, {
    onSuccess: (done) => toast(t("knowledge.reembedded", { count: done?.chunks ?? 0, seconds: ((done?.ms ?? 0) / 1000).toFixed(1) })),
  });

  if (kb.isPending) return <Loading />;
  if (kb.isError) return <ErrorNote error={kb.error} />;
  const { documents, chunks, embedder } = kb.data;
  return (
    <div className="space-y-6">
      <div className="stagger grid gap-3 sm:grid-cols-3">
        <StatTile icon="book" label={t("knowledge.documents")} value={documents.length} />
        <StatTile icon="tests" label={t("knowledge.passages")} value={chunks} />
        <div className="flex items-center"><Light ok={Boolean(embedder)} label={embedder ?? t("knowledge.no_embedder")} /></div>
      </div>
      {act.isError && <ErrorNote error={act.error} />}

      <section>
        <SectionTitle icon="book" title={t("knowledge.title")} action={
          <span className="flex gap-2">
            <Button variant="quiet" disabled={!embedder || act.isPending} onClick={() => reembed()}>{t("knowledge.reembed_all")}</Button>
            {!adding && <Button variant="primary" onClick={() => setAdding(true)}>{t("knowledge.add")}</Button>}
          </span>} />
        {adding && <AddDocument onDone={() => setAdding(false)} />}
        <div className="overflow-x-auto rounded-lg border border-hairline bg-raised">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-hairline text-muted">
              <tr>{["document", "licence", "tests", "passages", "cited", "actions"].map((c) => (
                <th key={c} className="px-3 py-2 font-medium">{t(`knowledge.c_${c}`)}</th>
              ))}</tr>
            </thead>
            <tbody className="divide-y divide-hairline">
              {documents.map((d) => (
                <tr key={d.id}>
                  <td className="px-3 py-2">
                    {d.url ? <a href={d.url} target="_blank" rel="noreferrer" className="font-medium text-link">{d.title} ↗</a>
                      : <span className="font-medium">{d.title}</span>}
                    <span className="block text-xs text-muted">
                      {[d.source_org, d.language.toUpperCase(), d.retrieved_at && t("knowledge.retrieved", { date: formatDate(d.retrieved_at, lang) })]
                        .filter(Boolean).join(" · ")}
                    </span>
                  </td>
                  <td className="px-3 py-2">{d.license}</td>
                  <td className="px-3 py-2">{d.tests.join(", ")}</td>
                  <td className="tabular px-3 py-2">{d.chunks}</td>
                  <td className="tabular px-3 py-2">{d.citations}</td>
                  <td className="px-3 py-2">
                    <span className="flex flex-wrap gap-3">
                      <button type="button" disabled={!embedder || act.isPending} className="text-link hover:underline disabled:opacity-50"
                        onClick={() => reembed(d.id)}>{t("knowledge.reembed")}</button>
                      <button type="button" disabled={act.isPending} className="text-abnormal hover:underline"
                        onClick={() => {
                          if (window.confirm(t("knowledge.delete_confirm", { title: d.title, count: d.citations }))) {
                            act.mutate({ kind: "delete", id: d.id }, { onSuccess: () => toast(t("knowledge.deleted")) });
                          }
                        }}>
                        {t("knowledge.delete")}
                      </button>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <p className="max-w-prose text-sm text-muted">{t("knowledge.note")}</p>
    </div>
  );
}

function AddDocument({ onDone }: { onDone: () => void }) {
  const { t } = useTranslation();
  const tests = useAdminCatalogue("");
  const act = useKnowledgeAction();
  const toast = useToast();
  const [doc, setDoc] = useState<KbDocumentIn>(EMPTY);
  const set = (patch: Partial<KbDocumentIn>) => setDoc({ ...doc, ...patch });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    act.mutate({ kind: "add", body: { ...doc, retrieved_at: doc.retrieved_at || undefined } }, {
      onSuccess: (made) => {
        toast(t("knowledge.added", { count: made?.chunks ?? 0 }));
        onDone();
      },
    });
  };
  const text = (f: "title" | "source_org" | "url", type = "text") => (
    <label className="text-sm">
      <span className="mb-1 block font-medium">{t(`knowledge.f_${f}`)}</span>
      <input type={type} value={doc[f]} required onChange={(e) => set({ [f]: e.target.value })} className={fieldClass} />
    </label>
  );
  return (
    <Card className="mb-5 p-5">
      <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
        {text("title")}
        {text("source_org")}
        {text("url", "url")}
        <label className="text-sm">
          <span className="mb-1 block font-medium">{t("knowledge.f_license")}</span>
          <input list="kb-licences" value={doc.license} required onChange={(e) => set({ license: e.target.value })} className={fieldClass} />
          <datalist id="kb-licences">{LICENCES.map((l) => <option key={l} value={l} />)}</datalist>
        </label>
        <label className="text-sm">
          <span className="mb-1 block font-medium">{t("knowledge.f_test")}</span>
          <select value={doc.test_code} required onChange={(e) => set({ test_code: e.target.value })} className={fieldClass}>
            <option value="">{t("knowledge.pick_test")}</option>
            {tests.data?.map((x) => <option key={x.code} value={x.code}>{x.name}</option>)}
          </select>
        </label>
        <div className="grid grid-cols-2 gap-3">
          <label className="text-sm">
            <span className="mb-1 block font-medium">{t("knowledge.f_language")}</span>
            <select value={doc.language} onChange={(e) => set({ language: e.target.value })} className={fieldClass}>
              {["en", "hi", "or"].map((l) => <option key={l} value={l}>{t(`knowledge.lang_${l}`)}</option>)}
            </select>
          </label>
          <label className="text-sm">
            <span className="mb-1 block font-medium">{t("knowledge.f_retrieved")}</span>
            <input type="date" value={doc.retrieved_at ?? ""} onChange={(e) => set({ retrieved_at: e.target.value })} className={fieldClass} />
          </label>
        </div>
        <div className="text-sm sm:col-span-2">
          <label htmlFor="kb-text" className="mb-1 block font-medium">{t("knowledge.f_text")}</label>
          <textarea id="kb-text" value={doc.text} required minLength={40} maxLength={20000} rows={8} aria-describedby="kb-text-hint"
            onChange={(e) => set({ text: e.target.value })} className={fieldClass} />
          <p id="kb-text-hint" className="mt-1 text-muted">{t("knowledge.text_hint")}</p>
        </div>
        {doc.language !== "en" && (
          <p className="flex items-center gap-2 text-sm text-borderline sm:col-span-2"><Icon name="info" size={16} />{t("knowledge.english_only")}</p>
        )}
        {act.isError && <div className="sm:col-span-2"><ErrorNote error={act.error} /></div>}
        <div className="flex gap-2 sm:col-span-2">
          <Button type="submit" variant="primary" disabled={act.isPending}>{t("knowledge.add_submit")}</Button>
          <Button type="button" onClick={onDone}>{t("common.cancel")}</Button>
        </div>
      </form>
    </Card>
  );
}
