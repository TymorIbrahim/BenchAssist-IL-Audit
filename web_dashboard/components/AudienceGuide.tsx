import { Card } from "./Card";

export function AudienceGuide() {
  return (
    <Card title="Who should use this dashboard?" className="audience-guide">
      <details open>
        <summary className="audience-summary">Who this dashboard is for — and who it is not for</summary>
        <div className="two-col audience-cols">
          <div>
            <h4>For</h4>
            <ul>
              <li>Legal experts reviewing flagged cases</li>
              <li>Responsible AI reviewers evaluating model behavior</li>
              <li>Researchers studying bias in language models</li>
              <li>Course reviewers evaluating the audit design</li>
            </ul>
          </div>
          <div>
            <h4>Not for</h4>
            <ul>
              <li>Litigants seeking legal advice</li>
              <li>Judges making actual decisions</li>
              <li>Production court deployment</li>
              <li>Legal certification of model safety</li>
            </ul>
          </div>
        </div>
      </details>
    </Card>
  );
}
