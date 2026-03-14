#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

# Cleanup script for memory entries that look like technical/test noise.
# Usage:
#   bash termux/cleanup-memory-noise.sh
#   CORE_URL=http://127.0.0.1:8000 bash termux/cleanup-memory-noise.sh --apply
#   bash termux/cleanup-memory-noise.sh --apply --extra-query "debug log"

CORE_URL="${CORE_URL:-http://127.0.0.1:8000}"
APPLY=0
LIMIT="${LIMIT:-50}"
EXTRA_QUERY=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)
      APPLY=1
      shift
      ;;
    --limit)
      LIMIT="$2"
      shift 2
      ;;
    --extra-query)
      EXTRA_QUERY="$2"
      shift 2
      ;;
    *)
      echo "Unknown arg: $1" >&2
      exit 2
      ;;
  esac
done

queries=(
  "smoke memory"
  "smoke"
  "test"
  "pytest"
  "unit test"
  "integration test"
  "debug"
  "traceback"
  "stack trace"
  "exception"
  "error log"
  "localhost"
  "127.0.0.1"
  "curl"
  "npm run"
  "poetry"
  "mypy"
  "py_compile"
  "termux"
  "sandbox"
  "api"
  "endpoint"
)

if [[ -n "$EXTRA_QUERY" ]]; then
  queries+=("$EXTRA_QUERY")
fi

echo "[info] CORE_URL=$CORE_URL"
echo "[info] mode=$([[ $APPLY -eq 1 ]] && echo APPLY || echo DRY-RUN)"

declare -A seen_ids=()
total_found=0
total_deleted=0

extract_items() {
  python - <<'PY'
import json,sys
payload=json.load(sys.stdin)
for item in payload.get('results', []):
    print(json.dumps({'id': item.get('id'), 'content': item.get('content','')[:180]}))
PY
}

for q in "${queries[@]}"; do
  body="$(python - <<'PYJSON' "$q" "$LIMIT"
import json,sys
print(json.dumps({"query": sys.argv[1], "limit": int(sys.argv[2])}))
PYJSON
)"

  response="$(curl -fsS -X POST "$CORE_URL/api/memory/search" \
    -H 'Content-Type: application/json' \
    -d "$body")" || {
      echo "[warn] search failed for query='$q'"
      continue
    }

  while IFS= read -r row; do
    [[ -z "$row" ]] && continue
    mid="$(python - <<'PY' "$row"
import json,sys
row=json.loads(sys.argv[1])
print(row.get('id') or '')
PY
)"
    snippet="$(python - <<'PY' "$row"
import json,sys
row=json.loads(sys.argv[1])
print(row.get('content') or '')
PY
)"

    [[ -z "$mid" ]] && continue
    if [[ -n "${seen_ids[$mid]:-}" ]]; then
      continue
    fi

    seen_ids[$mid]=1
    total_found=$((total_found + 1))
    echo "[match] id=$mid | query='$q' | snippet='${snippet//$'\n'/ }'"

    if [[ $APPLY -eq 1 ]]; then
      if curl -fsS -X DELETE "$CORE_URL/api/memory/$mid" >/dev/null; then
        total_deleted=$((total_deleted + 1))
        echo "[delete] id=$mid"
      else
        echo "[warn] delete failed for id=$mid"
      fi
    fi
  done < <(printf '%s' "$response" | extract_items)
done

echo "[summary] found=$total_found deleted=$total_deleted mode=$([[ $APPLY -eq 1 ]] && echo APPLY || echo DRY-RUN)"

if [[ $APPLY -eq 0 ]]; then
  echo "[hint] re-run with --apply to actually delete matched entries"
fi
