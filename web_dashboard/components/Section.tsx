import type { ReactNode } from "react";

export function Section({
  id,
  title,
  children,
  lead,
}: {
  id: string;
  title: string;
  lead?: string;
  children: ReactNode;
}) {
  return (
    <section id={id} className="section" aria-labelledby={`${id}-heading`}>
      <div className="section-header">
        <h2 id={`${id}-heading`}>{title}</h2>
        {lead ? <p className="section-lead">{lead}</p> : null}
      </div>
      <div className="section-content">{children}</div>
    </section>
  );
}
