export type DetentionTab =
  | "home"
  | "audit-results"
  | "case-review"
  | "mitigation"
  | "validity"
  | "reports"
  | "methodology";

export interface DetentionTabDef {
  id: DetentionTab;
  label: string;
  subtitle: string;
  icon?: string;
}

export const DETENTION_TABS: DetentionTabDef[] = [
  { id: "home", label: "Home", subtitle: "Overview", icon: "◎" },
  { id: "audit-results", label: "Audit Results", subtitle: "Dangerousness signals", icon: "◈" },
  { id: "case-review", label: "Case Review", subtitle: "Expert workspace", icon: "◫" },
  { id: "mitigation", label: "Mitigation", subtitle: "Prompt modes", icon: "◐" },
  { id: "validity", label: "Validity", subtitle: "Corpus & exclusions", icon: "◧" },
  { id: "reports", label: "Reports", subtitle: "Analysis exports", icon: "▤" },
  { id: "methodology", label: "Methodology", subtitle: "Scope & limits", icon: "◇" },
];

const LEGACY_TAB_MAP: Record<string, DetentionTab> = {
  overview: "home",
  findings: "audit-results",
  grounding: "methodology",
  statistical: "audit-results",
  "expert-workspace": "case-review",
  "real-cases": "methodology",
  "legal-reliability": "methodology",
  "run-comparison": "home",
};

export function parseDetentionTab(v: string | null): DetentionTab {
  if (v && LEGACY_TAB_MAP[v]) return LEGACY_TAB_MAP[v];
  const valid = DETENTION_TABS.map((t) => t.id);
  if (v && valid.includes(v as DetentionTab)) return v as DetentionTab;
  return "home";
}

export function tabLinkTarget(tab: DetentionTab): DetentionTab {
  return tab;
}
