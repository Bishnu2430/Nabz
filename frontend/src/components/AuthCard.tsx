import type { ReactNode } from "react";

import { Card } from "./ui";

/** The narrow sheet every sign-in page sits on: a seal, a title, the form, and links underneath. */
export function AuthCard({ title, intro, children, footer }: {
  title: string;
  intro?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className="rise mx-auto max-w-md py-4 sm:py-8">
      <Card className="p-6 sm:p-8">
        <img src="/seal.svg" alt="" className="hanko-stamped mb-4 size-10" />
        <h1 className="font-display text-3xl font-bold">{title}</h1>
        {intro && <div className="mt-2 text-muted">{intro}</div>}
        <div className="mt-6">{children}</div>
      </Card>
      {footer && <div className="mt-5 space-y-2 text-center text-muted">{footer}</div>}
    </div>
  );
}
