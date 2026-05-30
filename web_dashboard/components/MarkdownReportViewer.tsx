"use client";

import ReactMarkdown from "react-markdown";

export function MarkdownReportViewer({
  markdown,
  title,
}: {
  markdown: string;
  title?: string;
}) {
  if (!markdown.trim()) {
    return <p className="empty-inline">No report content available.</p>;
  }

  return (
    <article className="markdown-viewer" aria-label={title ?? "Report"}>
      <ReactMarkdown>{markdown}</ReactMarkdown>
    </article>
  );
}
