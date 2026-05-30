"use client";

import { useMemo, useState } from "react";
import { Badge } from "./Badge";
import { Card } from "./Card";
import { EmptyState } from "./EmptyState";
import { ExpandableText } from "./ExpandableText";
import { ReviewerQuestions } from "./ReviewerQuestions";
import { StatusPill } from "./StatusPill";
import { WhatChangedPanel } from "./WhatChangedPanel";
import { getCaseBadges, getCaseContext } from "@/lib/caseContext";
import {
  COMPARISON_MODE_LABELS,
  COMPARISON_TYPE_BY_MODE,
  CROSS_PROMPT_EMPTY_MESSAGE,
  crossPromptEmptyDetail,
  crossPromptToComparisonRow,
  getCrossPromptRow,
} from "@/lib/crossPromptComparison";
import { reviewPriorityVariant } from "@/lib/reviewPriority";
import { downloadReviewerPacket } from "@/lib/reviewerPacket";
import { copyShareLink } from "@/lib/urlState";
import { str, textDir, toBool } from "@/lib/format";
import type { DashboardData, JsonRecord } from "@/lib/types";

type FieldSpec = { label: string; neutralKey: string; variantKey: string };

const PAIR_FIELDS: FieldSpec[] = [
  { label: "Recommended action", neutralKey: "neutral_recommended_action_type", variantKey: "variant_recommended_action_type" },
  { label: "Urgency", neutralKey: "neutral_urgency_score", variantKey: "variant_urgency_score" },
  { label: "Remedy strength", neutralKey: "neutral_remedy_strength_score", variantKey: "variant_remedy_strength_score" },
  { label: "Evidence burden", neutralKey: "neutral_evidence_burden_score", variantKey: "variant_evidence_burden_score" },
  { label: "Credibility", neutralKey: "neutral_credibility_skepticism_score", variantKey: "variant_credibility_skepticism_score" },
  { label: "Rights orientation", neutralKey: "neutral_rights_orientation_score", variantKey: "variant_rights_orientation_score" },
  { label: "Procedural posture", neutralKey: "neutral_procedural_posture_score", variantKey: "variant_procedural_posture_score" },
  { label: "Reasoning", neutralKey: "neutral_reasoning_text", variantKey: "reasoning_text" },
];

export type ComparisonMode =
  | "neutral_vs_variant"
  | "baseline_vs_fairness"
  | "baseline_vs_blind"
  | "fairness_vs_blind"
  | "variant_to_variant";

function fieldChanged(row: JsonRecord, spec: FieldSpec): boolean {
  const n = str(row[spec.neutralKey]);
  const v = str(row[spec.variantKey]);
  if (!n && !v) return false;
  return n !== v;
}

function ComparisonField({
  label,
  neutralVal,
  variantVal,
  changed,
  leftLabel = "Neutral",
  rightLabel = "Variant",
}: {
  label: string;
  neutralVal: string;
  variantVal: string;
  changed: boolean;
  leftLabel?: string;
  rightLabel?: string;
}) {
  return (
    <div className={`comparison-field ${changed ? "field-changed" : ""}`}>
      <div className="field-label">{label}{changed ? " · changed" : ""}</div>
      <div className="comparison-pair-row">
        <div className="comparison-cell">
          <span className="cell-tag">{leftLabel}</span>
          <ExpandableText text={neutralVal || "—"} dir={textDir(neutralVal)} />
        </div>
        <div className="comparison-cell">
          <span className="cell-tag">{rightLabel}</span>
          <ExpandableText text={variantVal || "—"} dir={textDir(variantVal)} />
        </div>
      </div>
    </div>
  );
}

export function CaseComparison({
  row,
  data,
  comparisonMode,
  onComparisonModeChange,
  variantBId,
  onVariantBChange,
  variantsForCase = [],
  onPrev,
  onNext,
  hasPrev,
  hasNext,
  onBackToFlagged,
}: {
  row: JsonRecord | null;
  data: DashboardData;
  comparisonMode: ComparisonMode;
  onComparisonModeChange: (m: ComparisonMode) => void;
  variantBId?: string;
  onVariantBChange?: (id: string) => void;
  variantsForCase?: JsonRecord[];
  onPrev?: () => void;
  onNext?: () => void;
  hasPrev?: boolean;
  hasNext?: boolean;
  onBackToFlagged?: () => void;
}) {
  const [copied, setCopied] = useState(false);

  const caseId = str(row?.case_id);
  const variantId = str(row?.variant_id);
  const modeMeta = COMPARISON_MODE_LABELS[comparisonMode];
  const crossPromptAvailable = data.manifest.cross_prompt_comparisons_available ?? data.crossPromptComparisons.length > 0;

  const context = useMemo(() => {
    if (!row || !caseId || !variantId) return null;
    return getCaseContext(caseId, variantId, data);
  }, [row, caseId, variantId, data]);

  const badges = context ? getCaseBadges(context) : [];

  const comparisonRow = useMemo(() => {
    if (!row) return null;

    if (comparisonMode === "neutral_vs_variant") {
      if (!row.neutral_recommended_action_type && !row.variant_recommended_action_type) {
        return null;
      }
      return { ...row, _leftLabel: "Neutral", _rightLabel: str(row.variant_type).replace(/_/g, " ") || "Variant" };
    }

    if (comparisonMode === "variant_to_variant" && variantBId) {
      const b = variantsForCase.find((v) => str(v.variant_id) === variantBId);
      if (!b) return null;
      return {
        ...row,
        neutral_recommended_action_type: row.variant_recommended_action_type,
        variant_recommended_action_type: b.variant_recommended_action_type,
        neutral_urgency_score: row.variant_urgency_score,
        variant_urgency_score: b.variant_urgency_score,
        neutral_remedy_strength_score: row.variant_remedy_strength_score,
        variant_remedy_strength_score: b.variant_remedy_strength_score,
        neutral_reasoning_text: row.reasoning_text ?? row.variant_reasoning_text,
        reasoning_text: b.reasoning_text ?? b.variant_reasoning_text,
        _leftLabel: str(row.variant_type).replace(/_/g, " "),
        _rightLabel: str(b.variant_type).replace(/_/g, " "),
      } as JsonRecord;
    }

    const comparisonType = COMPARISON_TYPE_BY_MODE[comparisonMode];
    if (comparisonType) {
      const cross = getCrossPromptRow(data.crossPromptComparisons, caseId, variantId, comparisonType);
      if (!cross) return null;
      return crossPromptToComparisonRow(cross);
    }

    return row;
  }, [row, comparisonMode, variantBId, variantsForCase, data.crossPromptComparisons, caseId, variantId]);

  const emptyDetail = useMemo(() => {
    if (comparisonMode === "neutral_vs_variant") {
      return "Pairwise neutral-vs-variant data is missing for this case. Re-run the audit export or choose another case.";
    }
    if (comparisonMode === "variant_to_variant") {
      return variantBId
        ? "The second variant could not be loaded from pairwise data."
        : "Select a second variant from the same case to compare.";
    }
    return crossPromptEmptyDetail(comparisonMode, data.manifest);
  }, [comparisonMode, variantBId, data.manifest]);

  if (!row) {
    return (
      <EmptyState
        title="No case selected"
        description="Choose a case ID and variant above, open a flagged case, or use a share link."
        command="Tip: use Next/Previous flagged case once a case is selected."
      />
    );
  }

  const leftLabel = str(comparisonRow?._leftLabel || "Neutral");
  const rightLabel = str(comparisonRow?._rightLabel || "Variant");
  const priority = context?.reviewPriority ?? "Low";

  const handleCopyLink = async () => {
    const ok = await copyShareLink({
      section: "case-explorer",
      caseId,
      variantId,
      comparisonMode,
    });
    setCopied(ok);
    setTimeout(() => setCopied(false), 2000);
  };

  const isCrossPromptMode = Boolean(COMPARISON_TYPE_BY_MODE[comparisonMode]);

  return (
    <div className="case-comparison">
      <div className="explorer-toolbar">
        <div className="badge-row">
          {badges.map((b) => (
            <Badge key={b.label} variant={b.variant}>{b.label}</Badge>
          ))}
          <StatusPill label={`${priority} review priority`} variant={reviewPriorityVariant(priority)} />
        </div>
        <div className="explorer-nav">
          <button type="button" className="btn btn-ghost btn-sm" disabled={!hasPrev} onClick={onPrev}>← Previous flagged</button>
          <button type="button" className="btn btn-ghost btn-sm" disabled={!hasNext} onClick={onNext}>Next flagged →</button>
          <button type="button" className="btn btn-ghost btn-sm" onClick={handleCopyLink}>{copied ? "Link copied" : "Copy share link"}</button>
          {context ? (
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => downloadReviewerPacket(context, data)}>Download reviewer packet</button>
          ) : null}
          {onBackToFlagged ? (
            <button type="button" className="btn btn-secondary btn-sm" onClick={onBackToFlagged}>Back to flagged cases</button>
          ) : null}
        </div>
      </div>

      <Card title="Comparison mode">
        <div className="comparison-mode-row">
          <label>
            Mode
            <select value={comparisonMode} onChange={(e) => onComparisonModeChange(e.target.value as ComparisonMode)}>
              {(Object.keys(COMPARISON_MODE_LABELS) as ComparisonMode[]).map((mode) => (
                <option key={mode} value={mode}>{COMPARISON_MODE_LABELS[mode].label}</option>
              ))}
            </select>
          </label>
          {comparisonMode === "variant_to_variant" ? (
            <label>
              Second variant
              <select value={variantBId ?? ""} onChange={(e) => onVariantBChange?.(e.target.value)}>
                <option value="">Select…</option>
                {variantsForCase.filter((v) => str(v.variant_id) !== variantId).map((v) => (
                  <option key={str(v.variant_id)} value={str(v.variant_id)}>{str(v.variant_type).replace(/_/g, " ")}</option>
                ))}
              </select>
            </label>
          ) : null}
        </div>
        <p className="muted"><strong>{modeMeta.label}.</strong> {modeMeta.subtitle}</p>
        {isCrossPromptMode && !crossPromptAvailable ? (
          <p className="muted caution-line">{CROSS_PROMPT_EMPTY_MESSAGE}</p>
        ) : null}
      </Card>

      {!comparisonRow ? (
        <EmptyState
          title="Comparison data not available"
          description={emptyDetail}
          command={isCrossPromptMode ? "python -m benchassist.vercel_export --auto" : undefined}
        />
      ) : (
        <>
          {context ? (
            <Card title="Unified audit context">
              <p><strong>Why this priority?</strong> {context.reviewPriorityReason}</p>
              <p><strong>Strongest signal:</strong> {context.strongestSignal}</p>
              {comparisonRow._isCrossPrompt ? (
                <p className="muted">{str(comparisonRow.plain_language_summary)}</p>
              ) : null}
              {context.validity ? <p><strong>Validity:</strong> {str(context.validity.validity_category).replace(/_/g, " ")}</p> : null}
              {context.qualitative ? <p><strong>Qualitative note:</strong> {str(context.qualitative.summary || context.qualitative.reviewer_note).slice(0, 280)}</p> : null}
            </Card>
          ) : null}

          <Card title="Structured memo fields">
            {PAIR_FIELDS.map((spec) => (
              <ComparisonField
                key={spec.label}
                label={spec.label}
                neutralVal={str(comparisonRow[spec.neutralKey])}
                variantVal={str(comparisonRow[spec.variantKey])}
                changed={fieldChanged(comparisonRow, spec)}
                leftLabel={leftLabel}
                rightLabel={rightLabel}
              />
            ))}
          </Card>

          <WhatChangedPanel row={comparisonRow} />

          <Card title="Difference summary">
            <ul className="delta-list">
              <li><strong>Action changed?</strong> {toBool(comparisonRow.action_type_flip ?? comparisonRow.action_type_changed) ? "Yes" : "No"}</li>
              <li><strong>Urgency change</strong> {str(comparisonRow.urgency_delta ?? (comparisonRow.urgency_changed ? "changed" : "unchanged"))}</li>
              <li><strong>Remedy strength change</strong> {str(comparisonRow.remedy_strength_delta) || "—"}</li>
              <li><strong>Evidence burden change</strong> {str(comparisonRow.evidence_burden_delta ?? (comparisonRow.evidence_burden_changed ? "changed" : "unchanged"))}</li>
            </ul>
            <p className="muted caution-line">Screening signals only — human legal review required. Not proof of bias.</p>
          </Card>
        </>
      )}

      <Card title="Reviewer guidance">
        <p>
          Before treating this as a possible concern, check whether the facts are equivalent and whether the difference is legally justified.
          A higher evidence burden or weaker remedy may follow from changed facts — not from demographic cues alone.
        </p>
        <p className="muted caution-line">Screening signals only — not proof of unlawful discrimination.</p>
      </Card>

      <ReviewerQuestions title="Legal reviewer questions" />
    </div>
  );
}
