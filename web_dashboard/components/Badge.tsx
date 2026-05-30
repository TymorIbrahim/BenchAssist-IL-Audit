import type { ReactNode } from "react";

type BadgeVariant = "neutral" | "info" | "caution" | "concern" | "success";

const styles: Record<BadgeVariant, string> = {
  neutral: "badge-neutral",
  info: "badge-info",
  caution: "badge-caution",
  concern: "badge-concern",
  success: "badge-success",
};

export function Badge({
  children,
  variant = "neutral",
}: {
  children: ReactNode;
  variant?: BadgeVariant;
}) {
  return <span className={`badge ${styles[variant]}`}>{children}</span>;
}
