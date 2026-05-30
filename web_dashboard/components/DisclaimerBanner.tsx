export function DisclaimerBanner({ text }: { text: string }) {
  return (
    <div className="disclaimer-banner" role="note" aria-live="polite">
      {text}
    </div>
  );
}
