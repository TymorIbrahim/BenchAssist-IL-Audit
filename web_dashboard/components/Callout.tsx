import type { ReactNode } from "react";

export function Callout({
  title,
  children,
  variant = "info",
}: {
  title: string;
  children: ReactNode;
  variant?: "info" | "caution" | "success";
}) {
  return (
    <aside className={`callout callout-${variant}`}>
      <strong>{title}</strong>
      <div className="callout-body">{children}</div>
    </aside>
  );
}
