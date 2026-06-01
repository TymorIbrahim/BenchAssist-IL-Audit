"use client";

interface TooltipHelperProps {
  text: string;
}

export function TooltipHelper({ text }: TooltipHelperProps) {
  return (
    <span className="v2-tooltip-helper" aria-label={text}>
      <span className="v2-tooltip-helper__icon" tabIndex={0} role="img" aria-hidden="true">
        ?
      </span>
      <span className="v2-tooltip-helper__text">{text}</span>
    </span>
  );
}
