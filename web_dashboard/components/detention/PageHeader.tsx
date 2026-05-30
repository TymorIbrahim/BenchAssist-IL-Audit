"use client";

import { StatusPill } from "@/components/StatusPill";

export function PageHeader({
  title,
  subtitle,
  badges,
  actions,
  note,
}: {
  title: string;
  subtitle?: string;
  badges?: { label: string; variant?: "info" | "neutral" | "success" | "concern" | "caution" }[];
  actions?: React.ReactNode;
  note?: string;
}) {
  return (
    <header className="page-header detention-page-header">
      <div className="page-header-body">
        <h1>{title}</h1>
        {subtitle ? <p className="muted page-lead">{subtitle}</p> : null}
        {note ? <p className="page-note">{note}</p> : null}
        {badges?.length ? (
          <div className="page-badges">
            {badges.map((b) => (
              <StatusPill key={b.label} label={b.label} variant={b.variant ?? "info"} />
            ))}
          </div>
        ) : null}
      </div>
      {actions ? <div className="header-actions">{actions}</div> : null}
    </header>
  );
}
