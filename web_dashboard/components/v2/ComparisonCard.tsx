"use client";

import { useState } from "react";
import { ShiftBadge } from "./ShiftBadge";

interface ComparisonCardProps {
  neutralSummary?: string;
  neutralDangerousness?: string;
  neutralReasoning?: string;
  variantSummary?: string;
  variantDangerousness?: string;
  variantReasoning?: string;
  variantLabel?: string;
  baseCaseTitle?: string;
  isFlagged?: boolean;
  shiftDelta?: number;
  diffSummary?: string;
}

const REASONING_TRUNCATE_LENGTH = 400;

/* ---- Dangerousness level ordering for shift direction ---- */
const DANGER_ORDER: Record<string, number> = {
  insufficient_information: 0,
  low: 1,
  medium: 2,
  high: 3,
  very_high: 4,
};

function getShiftDirection(
  neutralDangerousness?: string,
  variantDangerousness?: string,
  shiftDelta?: number,
): "escalation" | "deescalation" | "unchanged" {
  if (shiftDelta != null) {
    if (shiftDelta > 0) return "escalation";
    if (shiftDelta < 0) return "deescalation";
    return "unchanged";
  }
  if (neutralDangerousness && variantDangerousness) {
    const nOrd = DANGER_ORDER[neutralDangerousness] ?? -1;
    const vOrd = DANGER_ORDER[variantDangerousness] ?? -1;
    if (vOrd > nOrd) return "escalation";
    if (vOrd < nOrd) return "deescalation";
  }
  return "unchanged";
}

function getDangerColor(level?: string): string {
  switch (level) {
    case "low": return "var(--v2-success)";
    case "medium": return "var(--v2-warning)";
    case "high":
    case "very_high": return "var(--v2-danger)";
    case "insufficient_information": return "var(--v2-text-muted)";
    default: return "var(--v2-text-secondary)";
  }
}

function formatDangerLevel(level?: string): string {
  if (!level) return "—";
  return level.replace(/_/g, " ");
}

function ReasoningBlock({ text }: { text?: string }) {
  const [expanded, setExpanded] = useState(false);

  if (!text) {
    return <p className="v2-comparison-card__reasoning--empty">No reasoning available</p>;
  }

  const needsTruncation = text.length > REASONING_TRUNCATE_LENGTH;
  const displayText =
    !expanded && needsTruncation
      ? text.slice(0, REASONING_TRUNCATE_LENGTH) + "…"
      : text;

  return (
    <div className="v2-comparison-card__reasoning">
      <p className="v2-comparison-card__reasoning-text">{displayText}</p>
      {needsTruncation && (
        <button
          type="button"
          className="v2-comparison-card__expand"
          onClick={() => setExpanded((prev) => !prev)}
        >
          {expanded ? "Show less" : "Show more"}
        </button>
      )}
    </div>
  );
}

export function ComparisonCard({
  neutralSummary,
  neutralDangerousness,
  neutralReasoning,
  variantSummary,
  variantDangerousness,
  variantReasoning,
  variantLabel = "Variant",
  baseCaseTitle,
  isFlagged = false,
  shiftDelta,
  diffSummary,
}: ComparisonCardProps) {
  const direction = getShiftDirection(
    neutralDangerousness,
    variantDangerousness,
    shiftDelta,
  );

  const dangerousnessChanged = neutralDangerousness !== variantDangerousness &&
    neutralDangerousness != null && variantDangerousness != null;

  return (
    <article className={`v2-comparison-card${isFlagged ? " v2-comparison-card--flagged" : ""}`}>
      {/* Header */}
      <header className="v2-comparison-card__header">
        <div>
          {baseCaseTitle && (
            <h3 className="v2-comparison-card__title">{baseCaseTitle}</h3>
          )}
          {diffSummary && (
            <p className="muted" style={{ marginTop: "0.2rem" }}>{diffSummary}</p>
          )}
        </div>
        <div className="v2-comparison-card__badges">
          <ShiftBadge direction={direction} delta={shiftDelta} />
          {isFlagged && <span className="v2-comparison-card__flag">⚑ Flagged</span>}
        </div>
      </header>

      {/* Two columns */}
      <div className="v2-comparison-card__columns">
        {/* Neutral */}
        <div className="v2-comparison-card__column">
          <h4 className="v2-comparison-card__column-title">Neutral Baseline</h4>
          {neutralSummary && (
            <p className="v2-comparison-card__summary">{neutralSummary}</p>
          )}
          <div
            className={`v2-comparison-card__danger-level${dangerousnessChanged ? "" : ""}`}
          >
            <span className="v2-comparison-card__danger-label">Dangerousness:</span>
            <span
              className="v2-comparison-card__danger-value"
              style={{ color: getDangerColor(neutralDangerousness), textTransform: "capitalize" }}
            >
              {formatDangerLevel(neutralDangerousness)}
            </span>
          </div>
          <ReasoningBlock text={neutralReasoning} />
        </div>

        {/* Variant */}
        <div className="v2-comparison-card__column">
          <h4 className="v2-comparison-card__column-title">{variantLabel}</h4>
          {variantSummary && (
            <p className="v2-comparison-card__summary">{variantSummary}</p>
          )}
          <div
            className={`v2-comparison-card__danger-level${dangerousnessChanged ? " v2-danger-mismatch" : ""}`}
          >
            <span className="v2-comparison-card__danger-label">Dangerousness:</span>
            <span
              className="v2-comparison-card__danger-value"
              style={{ color: getDangerColor(variantDangerousness), textTransform: "capitalize" }}
            >
              {formatDangerLevel(variantDangerousness)}
            </span>
            {dangerousnessChanged && (
              <span style={{ marginLeft: "auto", fontSize: "var(--v2-fs-xs)" }}>
                {neutralDangerousness?.replace(/_/g, " ")} → {variantDangerousness?.replace(/_/g, " ")}
              </span>
            )}
          </div>
          <ReasoningBlock text={variantReasoning} />
        </div>
      </div>
    </article>
  );
}
