/** Use-case-aware field labels for detention/remand audit dashboard. */

export const USE_CASE_LABELS: Record<string, string> = {
  housing: "BenchAssist-IL Housing Audit",
  detention: "BenchAssist-IL Detention Audit",
};

export const DETENTION_FIELD_LABELS: Record<string, string> = {
  dangerousness_level: "Dangerousness",
  obstruction_risk_level: "Obstruction risk",
  reasonable_suspicion_assessment: "Reasonable suspicion",
  investigative_necessity: "Investigative necessity",
  recommended_action_type: "Recommended action",
  recommended_duration_days: "Detention duration (days)",
  less_restrictive_alternatives_considered: "Less restrictive alternatives",
  procedural_safeguards_mentioned: "Procedural safeguards",
  suspect_credibility_framing: "Suspect credibility framing",
  rights_orientation: "Rights orientation",
  evidence_burden_level: "Evidence burden",
  legal_area: "Legal area",
  confidence: "Confidence",
  limitations: "Limitations",
};

export const DETENTION_DISCLAIMERS: string[] = [
  "Not legal advice.",
  "Not an AI judge.",
  "Synthetic/toy audit setting.",
  "Human legal review required.",
  "Metrics are screening signals, not proof of unlawful discrimination.",
  "The tool must not be used to make real detention decisions.",
  "Full-text real legal data is for internal expert review only.",
];

export function detentionFieldLabel(key: string): string {
  return DETENTION_FIELD_LABELS[key] ?? key.replace(/_/g, " ");
}

export function useCaseLabel(useCase: string): string {
  return USE_CASE_LABELS[useCase] ?? useCase;
}

export function isDetentionUseCase(useCase?: string): boolean {
  return (useCase ?? "").toLowerCase() === "detention";
}
