"use client";

export function DownloadButton({
  label,
  filename,
  content,
  mime = "text/csv",
  disabled = false,
}: {
  label: string;
  filename: string;
  content: string;
  mime?: string;
  disabled?: boolean;
}) {
  const handleClick = () => {
    if (!content || disabled) return;
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <button type="button" className="btn btn-secondary" onClick={handleClick} disabled={disabled || !content}>
      {label}
    </button>
  );
}
