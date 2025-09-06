#!/usr/bin/env bash
# Execute all `curl ...` commands found in a Markdown file (e.g., CURL_EXAMPLES.md).
# - Replaces placeholders with env values:
#     BASE_URL   -> replaces http://localhost:8000 and 127.0.0.1:8000 in URLs
#     JWT        -> replaces YOUR_TOKEN_HERE, YOUR_JWT_TOKEN_HERE, <JWT>, <TOKEN>
#     API_KEY    -> replaces YOUR_API_KEY_HERE, <API_KEY>, API_KEY_HERE
# - Supports line continuations with backslashes inside fenced code blocks.
# - DRY_RUN=1 to print commands without executing.
# - SKIP_DELETE=1 to skip any curl with -X DELETE.
#
# Usage:
#   DRY_RUN=1 BASE_URL="https://api.example.com" JWT="eyJ..." API_KEY="pl_key..." \
#     ./scripts/run_curls.sh ./CURL_EXAMPLES.md

set -euo pipefail

MD="${1:-./CURL_EXAMPLES.md}"
BASE_URL="${BASE_URL:-http://localhost:8000}"
JWT="${JWT:-}"
API_KEY="${API_KEY:-}"
DRY_RUN="${DRY_RUN:-0}"
SKIP_DELETE="${SKIP_DELETE:-0}"

if [[ ! -f "$MD" ]]; then
  echo "Markdown file not found: $MD" >&2
  exit 1
fi

tmp_cmds="$(mktemp)"
trap 'rm -f "$tmp_cmds"' EXIT

# Extract `curl ...` lines from fenced code blocks, merging backslash continuations.
# Use 'fenced' (not 'in') for mawk compatibility.
awk '
  BEGIN { fenced=0; buf="" }
  /^```/ { fenced = 1 - fenced; next }
  fenced {
    if ($1 == "curl") {
      if (buf != "") { print buf; buf="" }
      buf = $0; next
    }
    if (buf != "") {
      sub(/[[:space:]]+$/, "", buf)
      if (buf ~ /\\$/) {
        sub(/\\$/, "", buf)
        buf = buf " " $0
        next
      } else {
        print buf
        buf = ""
      }
    }
  }
  END { if (buf != "") print buf }
' "$MD" | sed '/^$/d' > "$tmp_cmds"

substitute() {
  local cmd="$1"
  # Replace localhost base with BASE_URL
  cmd="${cmd//http:\/\/localhost:8000/$BASE_URL}"
  cmd="${cmd//http:\/\/127.0.0.1:8000/$BASE_URL}"
  # JWT placeholders
  cmd="${cmd//YOUR_TOKEN_HERE/$JWT}"
  cmd="${cmd//YOUR_JWT_TOKEN_HERE/$JWT}"
  cmd="${cmd//<JWT>/$JWT}"
  cmd="${cmd//<TOKEN>/$JWT}"
  # API key placeholders
  cmd="${cmd//YOUR_API_KEY_HERE/$API_KEY}"
  cmd="${cmd//API_KEY_HERE/$API_KEY}"
  cmd="${cmd//<API_KEY>/$API_KEY}"
  echo "$cmd"
}

run_one() {
  local raw="$1"
  local cmd
  cmd="$(substitute "$raw")"

  if [[ "$SKIP_DELETE" == "1" && "$cmd" == *"-X DELETE"* ]]; then
    echo "⏭️  SKIP DELETE: $cmd"
    return 0
  fi

  echo "→ $cmd"
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "   (dry run)"
    return 0
  fi

  set +e
  # If user already added -w, just run it; else capture headers/body/http_code.
  if [[ "$cmd" == *" -w "* ]]; then
    eval "$cmd"
    rc=$?
  else
    eval "$cmd -sS -D /tmp/headers.$$ -o /tmp/body.$$ -w \"%{http_code}\""
    rc=$?
    if [[ $rc -eq 0 ]]; then
      code=$(tail -n1 /tmp/body.$$ | tr -d '\n')
      body_preview=$(head -c 200 /tmp/body.$$ | tr '\n' ' ')
      echo
      echo "   HTTP: $code  BODY: ${body_preview}"
      echo "   Headers:"
      head -n 5 /tmp/headers.$$ || true
    fi
    rm -f /tmp/headers.$$ /tmp/body.$$ || true
  fi
  set -e

  if [[ $rc -eq 0 ]]; then
    echo "✅ OK"
  else
    echo "❌ FAILED (exit $rc)"
    return $rc
  fi
}

total=0; ok=0; failc=0
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  total=$((total+1))
  if run_one "$line"; then
    ok=$((ok+1))
  else
    failc=$((failc+1))
  fi
done < "$tmp_cmds"

echo "———"
echo "Total: $total  OK: $ok  Failed: $failc"
[[ $failc -eq 0 ]] || exit 1
