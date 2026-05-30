import { Card } from "./Card";
import { getMetricDefinition } from "@/lib/metricDefinitions";
import { formatRate } from "@/lib/format";
import type { JsonRecord } from "@/lib/types";
import { str } from "@/lib/format";

export function MainFindingsStory({
  metricKey,
  metricValue,
  topGroups,
  onViewFlagged,
}: {
  metricKey: string;
  metricValue: unknown;
  topGroups: JsonRecord[];
  onViewFlagged: () => void;
}) {
  const def = getMetricDefinition(metricKey);

  return (
    <div className="findings-story">
      <Card title="What we measured">
        <p>{def?.plainMeaning ?? "Structured legal dimensions compared between neutral and variant memos for the same synthetic case."}</p>
      </Card>
      <Card title="What the main signal means">
        <p><strong>{def?.label ?? metricKey}:</strong> {formatRate(metricValue)} aggregate screening rate in this export.</p>
        <p className="muted">{def?.whyItMatters}</p>
      </Card>
      <Card title="Why legal experts should inspect this">
        <p>Differences in remedy, evidence demands, or credibility framing can affect access to relief — but may also be legally justified if facts differ. Check validity before treating a signal as a concern.</p>
        <p className="caution-line"><strong>Caution:</strong> {def?.caution ?? "Screening signal only — not proof of bias."}</p>
      </Card>
      {topGroups.length ? (
        <Card title="Top variant types (selected metric)">
          <ol>
            {topGroups.slice(0, 5).map((r) => (
              <li key={str(r.variant_type)}>{str(r.variant_type).replace(/_/g, " ")} — {formatRate(r[metricKey])}</li>
            ))}
          </ol>
          <button type="button" className="btn btn-secondary btn-sm" onClick={onViewFlagged}>View related flagged cases</button>
        </Card>
      ) : null}
    </div>
  );
}
