#!/usr/bin/env node
/** Fail CI if exported dashboard JSON contains invalid tokens (e.g. literal NaN). */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "public", "data");
const splitDir = path.join(root, "detention_case_review_records");

function walkJsonFiles(dir) {
  if (!fs.existsSync(dir)) return [];
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...walkJsonFiles(full));
    else if (entry.name.endsWith(".json")) out.push(full);
  }
  return out;
}

const files = [
  ...walkJsonFiles(root).filter((f) => !f.startsWith(splitDir)),
  ...walkJsonFiles(splitDir),
];

let failed = 0;
for (const file of files) {
  const raw = fs.readFileSync(file, "utf8");
  if (/\bNaN\b/.test(raw) || /\bInfinity\b/.test(raw)) {
    console.error(`invalid numeric token in ${path.relative(root, file)}`);
    failed += 1;
    continue;
  }
  try {
    JSON.parse(raw);
  } catch (err) {
    console.error(`JSON.parse failed for ${path.relative(root, file)}: ${err.message}`);
    failed += 1;
  }
}

if (failed) {
  console.error(`validate-export-json: ${failed} file(s) failed`);
  process.exit(1);
}

console.log(`validate-export-json: ${files.length} files OK`);
