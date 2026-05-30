export type StatusVariant =
  | "neutral"
  | "info"
  | "caution"
  | "concern"
  | "success"
  | "missing";

const styles: Record<StatusVariant, string> = {
  neutral: "status-neutral",
  info: "status-info",
  caution: "status-caution",
  concern: "status-concern",
  success: "status-success",
  missing: "status-missing",
};

export function StatusPill({
  label,
  variant = "neutral",
}: {
  label: string;
  variant?: StatusVariant;
}) {
  return <span className={`status-pill ${styles[variant]}`}>{label}</span>;
}
