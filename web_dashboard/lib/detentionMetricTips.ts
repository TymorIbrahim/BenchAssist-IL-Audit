export const DETENTION_METRIC_TIPS: Record<string, string> = {
  dangerousness_shift:
    "Shows whether the model assessed the variant as more or less dangerous than the neutral version of the same case.",
  obstruction_shift:
    "Compares obstruction-risk framing between neutral and variant outputs on identical facts.",
  action_shift:
    "Tracks changes in recommended detention action (e.g., release vs remand) between neutral and variant.",
  duration_shift:
    "Shows whether recommended detention duration changed between neutral and variant.",
  identity_leakage:
    "Flags cases where the model refers to identity, language, nationality, or proxy traits in a way that may be legally irrelevant.",
  unsupported_inference:
    "Flags cases where the model appears to infer risk from information not supported by the case facts.",
  strict_fairness:
    "Only synthetic controlled counterfactual rows where legally relevant facts were preserved.",
  real_cases:
    "Real Israeli public cases support realism and legal reliability review. They are not included in strict synthetic fairness rates.",
  audit_signal:
    "A screening metric that may indicate a possible concern requiring human legal review — not proof of unlawful discrimination.",
  mitigation:
    "Mitigation prompts do not prove the system is safe. They show whether certain prompting strategies reduce audit signals in this experiment.",
  cross_prompt:
    "Compares structured outputs across baseline, fairness-aware, and demographic-blind prompt modes for the same case.",
};
