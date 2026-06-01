"use client";

import { TooltipHelper } from "./TooltipHelper";

interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  variant?: "default" | "success" | "warning" | "danger";
  tooltip?: string;
}

export function StatCard({
  label,
  value,
  sub,
  variant = "default",
  tooltip,
}: StatCardProps) {
  const className = [
    "v2-stat-card",
    variant !== "default" ? `v2-stat-card--${variant}` : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={className}>
      <span className="v2-stat-card__label">
        {label}
        {tooltip && (
          <>
            {" "}
            <TooltipHelper text={tooltip} />
          </>
        )}
      </span>
      <span className="v2-stat-card__value">{value}</span>
      {sub && <span className="v2-stat-card__sub">{sub}</span>}
    </div>
  );
}
