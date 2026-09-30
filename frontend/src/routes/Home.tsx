import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { useProfiles } from "../api/hooks";
import type { Profile } from "../api/types";
import { ValueChips } from "../components/exact/exact";
import { ProfileForm } from "../components/ProfileForm";
import { Button, Card, EmptyState, ErrorNote, Loading, PageTitle } from "../components/ui";
import { formatDate } from "../lib/format";

export default function Home() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const profiles = useProfiles();
  const [adding, setAdding] = useState(false);

  if (profiles.isPending) return <Loading />;
  if (profiles.isError) return <ErrorNote error={profiles.error} onRetry={() => void profiles.refetch()} />;

  const created = (p: Profile) => navigate(`/p/${p.id}/upload`);

  if (profiles.data.length === 0) {
    return (
      <div className="mx-auto max-w-xl">
        <EmptyState title={t("home.empty_title")} body={t("home.empty_body")} />
        <Card className="p-6">
          <ProfileForm onCreated={created} />
        </Card>
      </div>
    );
  }

  return (
    <>
      <PageTitle
        title={t("home.title")}
        subtitle={t("home.subtitle")}
        action={!adding && <Button variant="primary" onClick={() => setAdding(true)}>{t("home.add_person")}</Button>}
      />
      {adding && (
        <Card className="mb-8 max-w-xl p-6">
          <ProfileForm onCreated={created} onCancel={() => setAdding(false)} />
        </Card>
      )}
      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {profiles.data.map((p) => (
          <li key={p.id}>
            <PersonCard profile={p} />
          </li>
        ))}
      </ul>
    </>
  );
}

function PersonCard({ profile }: { profile: Profile }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  const attention = profile.attention ?? [];
  return (
    <Card className="h-full p-5 transition hover:border-ink/40">
      <div className="flex items-baseline justify-between gap-3">
        <Link to={`/p/${profile.id}`} className="font-display text-xl font-bold text-ink no-underline hover:text-link">
          <h2>{profile.display_name}</h2>
        </Link>
        <span className="text-sm text-muted">{t(`profile_form.rel_${profile.relationship}`)}</span>
      </div>
      <p className="mt-1 text-sm text-muted">
        {t("home.reports", { count: profile.reports })}
        {profile.last_tested && <> · {t("home.last_tested", { date: formatDate(profile.last_tested, lang) })}</>}
      </p>
      <div className="mt-3">
        {attention.length > 0 ? (
          <>
            <p className="mb-1.5 text-sm font-medium">{t("home.attention", { count: attention.length })}</p>
            <ValueChips values={attention} max={4} linkTo={(v) => `/p/${profile.id}/tests/${v.test_code}`} />
          </>
        ) : profile.last_tested ? (
          <p className="text-sm text-normal">{t("home.all_in_range")}</p>
        ) : null}
      </div>
    </Card>
  );
}
