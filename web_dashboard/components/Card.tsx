import type { ReactNode } from "react";

export function Card({
  children,
  className = "",
  title,
  subtitle,
}: {
  children: ReactNode;
  className?: string;
  title?: string;
  subtitle?: string;
}) {
  return (
    <article className={`card ${className}`}>
      {title ? (
        <header className="card-header">
          <h3>{title}</h3>
          {subtitle ? <p className="card-subtitle">{subtitle}</p> : null}
        </header>
      ) : null}
      <div className="card-body">{children}</div>
    </article>
  );
}
