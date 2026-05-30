export type DetentionTab =
  | "home"
  | "audit-results"
  | "case-review"
  | "mitigation"
  | "real-cases"
  | "legal-reliability"
  | "expert-workspace"
  | "reports"
  | "methodology";

export interface DetentionTabDef {
  id: DetentionTab;
  label: string;
  subtitle: string;
  icon?: string;
}

export const DETENTION_TABS: DetentionTabDef[] = [
  { id: "home", label: "Home", subtitle: "Research story", icon: "◎" },
  { id: "audit-results", label: "Audit Results", subtitle: "Signals & metrics", icon: "◈" },
  { id: "case-review", label: "Case Review", subtitle: "Expert workspace", icon: "◫" },
  { id: "mitigation", label: "Mitigation", subtitle: "Prompt modes", icon: "◐" },
  { id: "real-cases", label: "Real Cases", subtitle: "Legal sources", icon: "◉" },
  { id: "legal-reliability", label: "Legal Reliability", subtitle: "Grounding & stats", icon: "◌" },
  { id: "reports", label: "Reports", subtitle: "Downloads", icon: "▤" },
  { id: "methodology", label: "Methodology", subtitle: "Scope & limits", icon: "◇" },
];

const LEGACY_TAB_MAP: Record<string, DetentionTab> = {
  overview: "home",
  findings: "audit-results",
  grounding: "legal-reliability",
  statistical: "legal-reliability",
  "expert-workspace": "case-review",
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
