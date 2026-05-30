import { Card } from "./Card";
import { runTypeLabel } from "@/lib/derive";
import { str } from "@/lib/format";
import type { Manifest } from "@/lib/types";

export function DataTransparency({ manifest }: { manifest: Manifest }) {
  const runLabel = runTypeLabel(str(manifest.run_type));

  return (
    <Card title="Data transparency" className="data-transparency">
      <details>
        <summary>Export metadata and why some sections may be empty</summary>
        <dl className="transparency-grid">
          <dt>Export timestamp</dt><dd>{manifest.timestamp || "Not available"}</dd>
          <dt>Run type</dt><dd>{runLabel} ({manifest.run_label})</dd>
          <dt>Provider / model</dt><dd>{manifest.provider} · {manifest.model}</dd>
          <dt>Prompt modes detected</dt><dd>{(manifest.prompt_modes_detected ?? manifest.prompt_modes ?? []).join(", ") || "Not available"}</dd>
          <dt>Schema versions</dt><dd>{(manifest.schema_versions ?? []).join(", ") || "Not available"}</dd>
          <dt>Row counts</dt>
          <dd>
            <ul className="compact-list">
              {Object.entries(manifest.row_counts ?? {}).map(([k, v]) => (
                <li key={k}>{k.replace(".json", "")}: {v}</li>
              ))}
            </ul>
          </dd>
          <dt>Missing optional files</dt>
          <dd>{manifest.missing_optional_files?.length ? manifest.missing_optional_files.join(", ") : "None listed"}</dd>
        </dl>
        <h4>Why some sections may be empty</h4>
        <p className="muted">
          Some sections require additional outputs such as grounded mode, statistical analysis, stereotype audit, or multiple prompt modes.
          Empty sections do not necessarily mean the audit found nothing — they may mean that artefact was not exported for this run.
        </p>
        <p className="muted">Refresh data: <code>python -m benchassist.vercel_export --auto</code></p>
      </details>
    </Card>
  );
}
