import { Callout } from "./Callout";
import { Card } from "./Card";

export function MethodologyContent() {
  return (
    <div className="methodology-content">
      <Callout title="Human legal review required" variant="caution">
        Metrics are screening signals, not proof of unlawful discrimination. A legally justified difference may exist.
      </Callout>

      <div className="method-grid">
        <Card title="What was audited">
          <p>A toy, non-binding judicial bench-memo assistant for Israeli housing disputes. Synthetic cases with counterfactual variants test whether legal framing changes when cues change.</p>
        </Card>
        <Card title="How the audit works">
          <p>Generate cases → create variants → run structured memos → compare neutral vs variant → flag differences → add validity, safety, and statistical checks → prepare human-review materials.</p>
        </Card>
        <Card title="What counts as an audit signal">
          <p>A structured change in remedy, evidence burden, credibility framing, rights orientation, urgency, or recommended action. It is a reason to inspect — not a verdict.</p>
        </Card>
        <Card title="Why counterfactual validity matters">
          <p>Strict counterfactuals preserve legal facts. Stress tests or added vulnerability cues require cautious interpretation and may not support direct comparison claims.</p>
        </Card>
        <Card title="Why human review is required">
          <p>Only legal experts can judge whether a difference is legally justified, factually equivalent, or materially harmful in a judicial workflow.</p>
        </Card>
        <Card title="What this dashboard can support">
          <ul><li>Research review and classroom presentation</li><li>Case triage and audit discussion</li><li>Transparent sharing of methods and results</li></ul>
        </Card>
        <Card title="What it cannot support">
          <ul><li>Legal advice or judicial decisions</li><li>Production deployment or fairness certification</li><li>Proof of discrimination</li></ul>
        </Card>
        <Card title="Main limitations">
          <ul>
            <li>Synthetic toy cases — limited domain (Israeli housing)</li>
            <li>Toy legal source grounding — not real legal research</li>
            <li>Single model / run snapshot — behavior may change</li>
            <li>Metrics are proxies — human review required</li>
            <li>Small samples may widen uncertainty</li>
          </ul>
        </Card>
      </div>
    </div>
  );
}
