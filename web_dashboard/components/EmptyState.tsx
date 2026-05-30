export function EmptyState({
  title,
  description,
  command,
  linkLabel,
  onLink,
}: {
  title: string;
  description: string;
  command?: string;
  linkLabel?: string;
  onLink?: () => void;
}) {
  return (
    <div className="empty-state" role="status">
      <h3>{title}</h3>
      <p>{description}</p>
      {command ? <p className="empty-command"><code>{command}</code></p> : null}
      {linkLabel && onLink ? (
        <button type="button" className="btn btn-secondary btn-sm" onClick={onLink}>{linkLabel}</button>
      ) : null}
    </div>
  );
}
