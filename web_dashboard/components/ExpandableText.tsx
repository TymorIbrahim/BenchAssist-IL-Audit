"use client";

import { useState } from "react";

export function ExpandableText({
  text,
  maxChars = 280,
  dir,
}: {
  text: string;
  maxChars?: number;
  dir?: "rtl" | "ltr" | "auto";
}) {
  const [expanded, setExpanded] = useState(false);
  if (!text) return <span>—</span>;
  const needsExpand = text.length > maxChars;
  const display = expanded || !needsExpand ? text : `${text.slice(0, maxChars)}…`;

  return (
    <div className="expandable-text">
      <div dir={dir}>{display}</div>
      {needsExpand ? (
        <button type="button" className="link-button" onClick={() => setExpanded(!expanded)}>
          {expanded ? "Show less" : "Show full text"}
        </button>
      ) : null}
    </div>
  );
}
