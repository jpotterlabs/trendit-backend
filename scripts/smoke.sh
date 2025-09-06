#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
JWT="${JWT:-}"
API_KEY="${API_KEY:-}"
ENDPOINTS_FILE="${1:-/mnt/data/endpoints.txt}"

pass(){ echo "✅ $*"; }
fail(){ echo "❌ $*"; exit 1; }

test_one() {
  local method="$1" path="$2" body="${3:-}"
  local url="${BASE_URL}${path}"

  # Happy path (authorized)
  http_code=$(curl -sS -m 30 -o /tmp/out.json -w "%{http_code}" \
    -X "$method" "$url" \
    -H "Authorization: Bearer $JWT" \
    -H "X-API-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    ${body:+--data "$body"} )
  if [[ ! "$http_code" =~ ^2 ]]; then
    echo "Response body:"
    cat /tmp/out.json || true
    fail "Happy-path ${method} ${path} -> HTTP $http_code"
  fi

  # Unauthorized (no creds) should be 401/403 (skip auth endpoints)
  if [[ "$path" != *"/auth/login"* && "$path" != *"/auth/register"* ]]; then
    http_unauth=$(curl -sS -m 15 -o /dev/null -w "%{http_code}" -X "$method" "$url")
    [[ "$http_unauth" == "401" || "$http_unauth" == "403" ]] || \
      fail "Unauthorized should be 401/403 for ${method} ${path}, got $http_unauth"
  fi

  # Optional: check quota headers (ignore if absent)
  curl -sS -m 10 -I -X "$method" "$url" \
    -H "Authorization: Bearer $JWT" -H "X-API-Key: $API_KEY" >/tmp/headers.txt || true
  grep -qi "^X-RateLimit-Limit:"     /tmp/headers.txt && pass "${path} has X-RateLimit-Limit" || true
  grep -qi "^X-RateLimit-Remaining:" /tmp/headers.txt && pass "${path} has X-RateLimit-Remaining" || true
  grep -qi "^X-User-Tier:"           /tmp/headers.txt && pass "${path} has X-User-Tier" || true

  pass "${method} ${path}"
}

# Force-429 helper (optional): call the endpoint N times to exceed limit
force_429() {
  local method="$1" path="$2" body="${3:-}" n="${4:-0}"
  [[ "${n}" =~ ^[0-9]+$ ]] || return 0
  [[ "$n" -gt 0 ]] || return 0
  for i in $(seq 1 "$n"); do
    code=$(curl -sS -o /dev/null -w "%{http_code}" -X "$method" "${BASE_URL}${path}" \
      -H "Authorization: Bearer $JWT" -H "X-API-Key: $API_KEY" \
      -H "Content-Type: application/json" ${body:+--data "$body"})
    if [[ "$code" == "429" ]]; then
      pass "Hit 429 on ${path} after $i calls"
      return 0
    fi
  done
  fail "Did not hit 429 on ${path} after ${n} calls"
}

while IFS= read -r line; do
  [[ -z "$line" || "$line" =~ ^# ]] && continue

  # Split into method, path, (optional) JSON body, (optional) N
  method=$(echo "$line" | awk '{print $1}')
  path=$(echo "$line"   | awk '{print $2}')
  rest=$(echo "$line"   | awk '{$1="";$2="";sub(/^  */,"");print}')

  # If "rest" ends with an integer, treat it as FORCE_429_AFTER_N
  n=""
  if [[ "$rest" =~ [[:space:]]([0-9]+)$ ]]; then
    n="${BASH_REMATCH[1]}"
    body="${rest% $n}"
  else
    body="$rest"
  fi

  # Trim surrounding quotes if present
  body="${body#\'}"; body="${body%\'}"
  body="${body#\"}"; body="${body%\"}"

  test_one "$method" "$path" "$body"

  # Optional forced 429 test
  [[ -n "$n" ]] && force_429 "$method" "$path" "$body" "$n"
done < "$ENDPOINTS_FILE"

echo "🎯 All smoke tests passed."
