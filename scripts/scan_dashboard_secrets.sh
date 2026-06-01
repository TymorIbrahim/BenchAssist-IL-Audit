#!/usr/bin/env bash
# Fail if common secret patterns appear in dashboard public data.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA="${ROOT}/web_dashboard/public/data"
if [[ ! -d "$DATA" ]]; then
  echo "No public/data directory — skip"
  exit 0
fi
if rg -n --glob '*.json' -e 'GEMINI_API_KEY|GOOGLE_API_KEY|sk-[a-zA-Z0-9]{20,}|AIza[0-9A-Za-z_-]{30,}' "$DATA"; then
  echo "ERROR: Possible secret material in dashboard export"
  exit 1
fi
echo "Secret scan passed for $DATA"
