import { SECTION_GUIDES } from "@/lib/sectionGuides";

export function SectionGuide({ sectionId }: { sectionId: string }) {
  const guide = SECTION_GUIDES[sectionId];
  if (!guide) return null;
  return (
    <div className="section-guide" aria-label="Section guide">
      <p><span className="guide-label">What this shows:</span> {guide.what}</p>
      <p><span className="guide-label">How to interpret it:</span> {guide.interpret}</p>
      <p><span className="guide-label">What to review next:</span> {guide.next}</p>
    </div>
  );
}
