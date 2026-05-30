import type { ReportEntry } from "./types";

export interface ReportCategory {
  id: string;
  title: string;
  description: string;
  match: (r: ReportEntry) => boolean;
}

export const REPORT_CATEGORIES: ReportCategory[] = [
  {
    id: "final",
    title: "Final reports",
    description: "Primary audit write-ups, results interpretation, and limitations.",
    match: (r) => /final_audit|results_interpretation|limitations_and_risks|limitations/i.test(r.report_name + r.title),
  },
  {
    id: "course",
    title: "Course / presentation",
    description: "Worldbuilding template and presentation notes for demos.",
    match: (r) => /worldbuilding|presentation/i.test(r.report_name + r.title),
  },
  {
    id: "audit_details",
    title: "Audit details",
    description: "Counterfactual validity, stereotype, hallucination, statistical analysis, narrative robustness, and qualitative case studies.",
    match: (r) =>
      /validity|statistical|counterfactual|stereotype|hallucination|narrative|qualitative|grounding|human_review/i.test(
        r.report_name + r.title,
      ),
  },
];

export const RECOMMENDED_READING = [
  "final_audit_report",
  "results_interpretation",
  "limitations_and_risks",
  "presentation_notes",
  "qualitative_case_studies",
  "counterfactual_validity",
];

export function categorizeReports(reports: ReportEntry[]): Record<string, ReportEntry[]> {
  const buckets: Record<string, ReportEntry[]> = Object.fromEntries(REPORT_CATEGORIES.map((c) => [c.id, []]));
  const other: ReportEntry[] = [];
  for (const report of reports) {
    let placed = false;
    for (const cat of REPORT_CATEGORIES) {
      if (cat.match(report)) {
        buckets[cat.id].push(report);
        placed = true;
        break;
      }
    }
    if (!placed) other.push(report);
  }
  if (other.length) buckets.other = other;
  return buckets;
}
