import clsx from "clsx";
import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../api/client";
import { Enso } from "./Enso";
import { Icon, IconSeal, type IconName } from "./icons";

type Variant = "primary" | "secondary" | "quiet" | "danger";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-accent text-accent-ink hover:brightness-110 border-transparent",
  secondary: "bg-raised text-ink border-hairline hover:border-ink/40",
  quiet: "bg-transparent text-link border-transparent hover:underline",
  danger: "bg-transparent text-abnormal border-abnormal/40 hover:bg-abnormal/10",
};

export function Button({ variant = "secondary", className, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      type="button"
      {...props}
      className={clsx(
        "btn inline-flex items-center justify-center gap-2 rounded-md border px-4 py-2 font-medium",
        variant === "primary" && "btn-primary",
        "disabled:cursor-not-allowed disabled:opacity-50",
        VARIANTS[variant],
        className,
      )}
    />
  );
}

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={clsx("card rounded-lg border border-hairline bg-raised", className)}>{children}</div>;
}

export function PageTitle({ title, subtitle, action, icon, mark }: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  /** The page's mark, set in a seal beside the title. */
  icon?: IconName;
  /** Anything else to put beside the title instead of an icon, e.g. a person's seal. */
  mark?: ReactNode;
}) {
  return (
    <div className="page-head mb-8 flex flex-wrap items-end justify-between gap-4">
      <div className="flex items-start gap-4">
        {mark ?? (icon && <IconSeal name={icon} size={24} className="icon-seal-lg mt-1" />)}
        <div>
          <h1 className="font-display text-3xl font-bold sm:text-4xl">{title}</h1>
          {subtitle && <p className="mt-2 max-w-prose text-muted">{subtitle}</p>}
        </div>
      </div>
      {action}
    </div>
  );
}

/** A section's heading with its mark, and an optional action on the right. */
export function SectionTitle({ id, icon, title, action, className }: {
  id?: string;
  icon?: IconName;
  title: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={clsx("mb-3 flex flex-wrap items-center justify-between gap-3", className)}>
      <h2 id={id} className="flex items-center gap-2.5 font-display text-xl font-bold">
        {icon && <IconSeal name={icon} />}
        {title}
      </h2>
      {action}
    </div>
  );
}

/** Nothing here yet, said quietly: the section's mark in a dashed circle and one line. */
export function Empty({ icon, children, className }: { icon: IconName; children: ReactNode; className?: string }) {
  return (
    <div className={clsx("flex items-center gap-4 rounded-lg border border-dashed border-hairline px-5 py-4 text-muted", className)}>
      <span className="empty-mark"><Icon name={icon} size={22} /></span>
      <div>{children}</div>
    </div>
  );
}

/** A brush stroke between the parts of a long page. */
export function BrushRule() {
  return <div className="brush-rule" aria-hidden="true" />;
}

const SEAL_INKS = 5; // --seal-1 … --seal-5 in styles/polish.css

/** A person's initial as a name seal, its ink chosen from their name so it stays the same everywhere. */
export function PersonSeal({ name, large }: { name: string; large?: boolean }) {
  const ink = ([...name].reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 0) % SEAL_INKS) + 1;
  return (
    <span aria-hidden="true" className={clsx("avatar-seal", large && "avatar-seal-lg")}
      style={{ ["--seal" as string]: `var(--seal-${ink})` }}>
      {[...name.trim()][0]?.toUpperCase()}
    </span>
  );
}

export function EmptyState({ title, body, action }: { title: string; body: string; action?: ReactNode }) {
  return (
    <div className="mx-auto max-w-md py-16 text-center">
      {/* a single ink stroke: ma, the empty space, is the design */}
      <svg aria-hidden="true" viewBox="0 0 200 20" className="mx-auto mb-6 w-40 text-ink/60">
        <path d="M6 12 C 50 4, 110 16, 194 8" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
      </svg>
      <h2 className="font-display text-2xl font-bold">{title}</h2>
      <p className="mt-2 text-muted">{body}</p>
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}

/** What went wrong, in the reader's language when the API gave a reason code; its English words otherwise. */
export function useErrorText() {
  const { t, i18n } = useTranslation();
  return (error: unknown): string => {
    if (!(error instanceof ApiError)) return t("common.error");
    const key = error.code && `errors.${error.code}`;
    return key && i18n.exists(key) ? t(key, error.body as Record<string, string>) : error.message;
  };
}

export function ErrorNote({ error, message, onRetry }: { error?: unknown; message?: string; onRetry?: () => void }) {
  const { t } = useTranslation();
  const describe = useErrorText();
  message ??= describe(error);
  return (
    <div role="alert" className="rounded-md border border-abnormal/40 bg-abnormal/5 px-4 py-3 text-abnormal">
      <p>{message}</p>
      {onRetry && (
        <Button variant="quiet" className="mt-1 px-0" onClick={onRetry}>{t("common.retry")}</Button>
      )}
    </div>
  );
}

/** The brush circle drawing itself while a page's data arrives. */
export function Loading() {
  const { t } = useTranslation();
  return (
    <div className="fade-in py-14 text-center">
      <Enso label={t("common.loading")} size={72} />
    </div>
  );
}

export const fieldClass =
  "w-full rounded-md border border-hairline bg-surface px-3 py-2 text-ink placeholder:text-muted/70 focus:border-ink/50";

/** A labelled input with an optional hint and error, wired up for screen readers. */
export function Field({ id, label, hint, error, className, ...input }: InputHTMLAttributes<HTMLInputElement> & {
  id: string;
  label: string;
  hint?: ReactNode;
  error?: string;
}) {
  const describedBy = [hint && `${id}-hint`, error && `${id}-error`].filter(Boolean).join(" ") || undefined;
  return (
    <div className={className}>
      <label htmlFor={id} className="mb-1 block font-medium">{label}</label>
      <input id={id} {...input} aria-invalid={error ? true : undefined} aria-describedby={describedBy}
        className={clsx(fieldClass, error && "border-abnormal")} />
      {hint && <p id={`${id}-hint`} className="mt-1 text-sm text-muted">{hint}</p>}
      {error && <p id={`${id}-error`} className="mt-1 text-sm text-abnormal">{error}</p>}
    </div>
  );
}

/** A quiet confirmation line, e.g. "Your password is changed." */
export function Notice({ children }: { children: ReactNode }) {
  return <p role="status" className="rounded-md border border-normal/40 bg-normal/5 px-4 py-3 text-normal">{children}</p>;
}
