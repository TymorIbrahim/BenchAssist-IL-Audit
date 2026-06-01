"use client";

interface EmptyStateProps {
  title?: string;
  message?: string;
  icon?: string;
}

export function EmptyState({
  title = "No data available",
  message = "There are no results matching the current filters.",
  icon = "∅",
}: EmptyStateProps) {
  return (
    <div className="v2-empty-state" role="status">
      {icon && <span className="v2-empty-state__icon">{icon}</span>}
      <h3 className="v2-empty-state__title">{title}</h3>
      <p className="v2-empty-state__message">{message}</p>
    </div>
  );
}
