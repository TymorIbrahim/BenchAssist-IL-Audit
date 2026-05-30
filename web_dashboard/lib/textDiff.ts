export type DiffLineKind = "same" | "removed" | "added" | "changed";

export interface DiffLine {
  kind: DiffLineKind;
  base?: string;
  variant?: string;
}

/** Simple line-level diff for case text comparison (RTL-safe display). */
export function diffLines(baseText: string, variantText: string): DiffLine[] {
  const baseLines = (baseText || "").split(/\r?\n/);
  const variantLines = (variantText || "").split(/\r?\n/);
  const out: DiffLine[] = [];

  let variantOffset = 0;
  if (variantLines.length > baseLines.length && baseLines.length > 0) {
    const maxOffset = Math.min(variantLines.length - baseLines.length, 6);
    let bestOffset = 0;
    let bestScore = -1;
    for (let offset = 0; offset <= maxOffset; offset++) {
      let score = 0;
      for (let i = 0; i < baseLines.length; i++) {
        if (baseLines[i] === variantLines[offset + i]) score += 1;
      }
      if (score > bestScore) {
        bestScore = score;
        bestOffset = offset;
      }
    }
    if (bestScore >= Math.max(2, Math.floor(baseLines.length * 0.5))) {
      variantOffset = bestOffset;
    }
  }

  for (let i = 0; i < variantOffset; i++) {
    out.push({ kind: "added", variant: variantLines[i] });
  }

  const alignedVariant = variantLines.slice(variantOffset);
  const max = Math.max(baseLines.length, alignedVariant.length);
  for (let i = 0; i < max; i++) {
    const b = baseLines[i];
    const v = alignedVariant[i];
    if (b === undefined && v !== undefined) {
      out.push({ kind: "added", variant: v });
    } else if (b !== undefined && v === undefined) {
      out.push({ kind: "removed", base: b });
    } else if (b === v) {
      out.push({ kind: "same", base: b, variant: v });
    } else {
      out.push({ kind: "changed", base: b, variant: v });
    }
  }
  return out;
}

export function diffHasChanges(lines: DiffLine[]): boolean {
  return lines.some((l) => l.kind !== "same");
}
