"use client";

interface ShiftBadgeProps {
  direction: "escalation" | "deescalation" | "unchanged";
  delta?: number;
}

const ARROW_MAP: Record<ShiftBadgeProps["direction"], string> = {
  escalation: "↑",
  deescalation: "↓",
  unchanged: "—",
};

export function ShiftBadge({ direction, delta }: ShiftBadgeProps) {
  const arrow = ARROW_MAP[direction];
  const displayDelta =
    delta != null
      ? direction === "escalation" && delta > 0
        ? `+${delta}`
        : String(delta)
      : null;

  return (
    <span className={`v2-shift-badge v2-shift-badge--${direction}`}>
      <span className="v2-shift-badge__arrow">{arrow}</span>
      {displayDelta != null && (
        <span className="v2-shift-badge__delta">{displayDelta}</span>
      )}
    </span>
  );
}
