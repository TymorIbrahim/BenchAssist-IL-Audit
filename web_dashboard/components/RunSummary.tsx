"use client";

import { useState } from "react";
import { detectRunType, runTypeLabel } from "@/lib/derive";
import { formatDate } from "@/lib/format";
import type { Manifest } from "@/lib/types";
import { StatusPill } from "./StatusPill";

export function RunSummary({ manifest }: { manifest: Manifest }) {
  const [expanded, setExpanded] = useState(false);
  const runType = manifest.run_type ?? detectRunType(manifest.run_label);
  const files = Object.entries(manifest.selected_source_files ?? {}).filter(([name]) => {
    if (manifest.use_case !== "detention") return true;
    return name !== "model_outputs.csv" && !name.startsWith("model_outputs");
  });

  return (
    <div className="run-summary">
      <div className="run-summary-header">
        <div>
          <h4>Loaded run</h4>
          <p className="muted">Last exported {formatDate(manifest.timestamp)}</p>
        </div>
        <StatusPill label={runTypeLabel(runType)} variant={runType === "mock" ? "caution" : "info"} />
      </div>
      <dl className="run-summary-grid">
        <div><dt>Model</dt><dd>{manifest.model}</dd></div>
        <div><dt>Provider</dt><dd>{manifest.provider}</dd></div>
        <div><dt>Prompt mode</dt><dd>{manifest.prompt_mode}</dd></div>
        <div><dt>Flagged cases</dt><dd>{manifest.flagged_cases ?? "—"}</dd></div>
      </dl>
      <button type="button" className="link-button" onClick={() => setExpanded(!expanded)}>
        {expanded ? "Hide loaded files" : "Show loaded files"}
      </button>
      {expanded ? (
        <ul className="file-list">
          {files.map(([name, path]) => (
            <li key={name}>
              <strong>{name}</strong>
              <span className="muted">{path ?? "not available"}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
