#!/usr/bin/env bash
set -euo pipefail

# Check raw internet access plus optional Roampal online-tools API.
# Verifies three capabilities:
#  1) access to an external URL
#  2) receiving structured info from the internet
#  3) downloading a file from the internet
# If the local core API is reachable, also verifies /api/online/health,
# /api/online/search and /api/online/download.

HOST_CORE="${HOST_CORE:-http://127.0.0.1:8000}"
ACCESS_URL="${ACCESS_URL:-https://api.github.com/}"
INFO_URL="${INFO_URL:-https://api.github.com/repos/Wvwvwvwvwv/jubilant-computing-machine}"
DOWNLOAD_URL="${DOWNLOAD_URL:-https://raw.githubusercontent.com/Wvwvwvwvwv/jubilant-computing-machine/main/README.md}"
SEARCH_QUERY="${SEARCH_QUERY:-latest python release}"
OUT_DIR="${OUT_DIR:-logs}"
STRICT="${STRICT:-0}"
CHECK_API="${CHECK_API:-1}"

mkdir -p "$OUT_DIR"
TS="$(date +%Y%m%d-%H%M%S)"
DIRECT_DOWNLOAD_PATH="$OUT_DIR/internet-download-$TS.bin"
API_REPORT_JSON="$OUT_DIR/online-tools-report-$TS.json"
INFO_JSON="$OUT_DIR/internet-info-$TS.json"

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[error] required command missing: $1" >&2
    exit 127
  fi
}

need_cmd curl
need_cmd python3

warn_or_fail() {
  local message="$1"
  echo "[warn] $message" >&2
  if [[ "$STRICT" == "1" ]]; then
    exit 2
  fi
}

echo "== Online tools / internet sanity check =="
echo "out dir: $OUT_DIR"
echo "core url: $HOST_CORE"

echo "[1/5] Direct internet access: $ACCESS_URL"
ACCESS_CODE="$(curl -L -sS -o /dev/null -w '%{http_code}' --max-time 20 "$ACCESS_URL" || true)"
if [[ ! "$ACCESS_CODE" =~ ^2|3 ]]; then
  warn_or_fail "cannot reach ACCESS_URL=$ACCESS_URL (http_code=$ACCESS_CODE)"
else
  echo "[ok] external access works (http_code=$ACCESS_CODE)"
fi

echo "[2/5] Structured internet info: $INFO_URL"
INFO_CODE="$(curl -L -sS -o "$INFO_JSON" -w '%{http_code}' --max-time 25 \
  -H 'Accept: application/vnd.github+json' \
  -H 'User-Agent: roampal-online-check' \
  "$INFO_URL" || true)"
if [[ ! "$INFO_CODE" =~ ^2 ]]; then
  warn_or_fail "cannot fetch structured info from INFO_URL=$INFO_URL (http_code=$INFO_CODE)"
else
  python3 - <<'PY' "$INFO_JSON"
import json, sys
path = sys.argv[1]
data = json.load(open(path, encoding='utf-8'))
summary = {
    'name': data.get('name'),
    'full_name': data.get('full_name'),
    'default_branch': data.get('default_branch'),
    'visibility': 'private' if data.get('private') else 'public',
}
print('[ok] structured info received:', json.dumps(summary, ensure_ascii=False))
PY
fi

echo "[3/5] Direct internet download: $DOWNLOAD_URL"
DOWNLOAD_CODE="$(curl -L -sS -o "$DIRECT_DOWNLOAD_PATH" -w '%{http_code}' --max-time 30 "$DOWNLOAD_URL" || true)"
if [[ ! "$DOWNLOAD_CODE" =~ ^2 ]]; then
  warn_or_fail "cannot download DOWNLOAD_URL=$DOWNLOAD_URL (http_code=$DOWNLOAD_CODE)"
else
  python3 - <<'PY' "$DIRECT_DOWNLOAD_PATH"
from pathlib import Path
import sys
p = Path(sys.argv[1])
size = p.stat().st_size if p.exists() else 0
assert size > 0, f'empty download: {p}'
print(f'[ok] file downloaded: {p} ({size} bytes)')
PY
fi

echo "[4/5] Optional local online API checks"
if [[ "$CHECK_API" != "1" ]]; then
  echo "[skip] CHECK_API=0"
else
  HEALTH_CODE="$(curl -sS -o "$OUT_DIR/online-health-$TS.json" -w '%{http_code}' --max-time 10 "$HOST_CORE/api/online/health" || true)"
  if [[ ! "$HEALTH_CODE" =~ ^2 ]]; then
    warn_or_fail "local online health endpoint is not reachable: $HOST_CORE/api/online/health (http_code=$HEALTH_CODE)"
  else
    ENABLED="$(python3 - <<'PY' "$OUT_DIR/online-health-$TS.json"
import json, sys
print(str(bool(json.load(open(sys.argv[1], encoding='utf-8')).get('enabled'))).lower())
PY
)"
    if [[ "$ENABLED" != "true" ]]; then
      warn_or_fail "online tools API reachable but disabled; export ENABLE_ONLINE_TOOLS=1"
    else
      echo "[ok] local /api/online/health reports enabled=true"

      SEARCH_BODY="$(python3 - <<'PY'
import json, os
print(json.dumps({'query': os.environ.get('SEARCH_QUERY', 'latest python release'), 'limit': 3}, ensure_ascii=False))
PY
)"
      curl -fsS -X POST "$HOST_CORE/api/online/search" \
        -H 'Content-Type: application/json' \
        -d "$SEARCH_BODY" > "$OUT_DIR/online-search-$TS.json"

      DOWNLOAD_BODY="$(python3 - <<'PY'
import json, os
url = os.environ['DOWNLOAD_URL']
filename = os.path.basename(url) or 'download.bin'
print(json.dumps({'url': url, 'filename': filename}, ensure_ascii=False))
PY
)"
      curl -fsS -X POST "$HOST_CORE/api/online/download" \
        -H 'Content-Type: application/json' \
        -d "$DOWNLOAD_BODY" > "$OUT_DIR/online-download-$TS.json"

      python3 - <<'PY' "$OUT_DIR/online-search-$TS.json" "$OUT_DIR/online-download-$TS.json" "$API_REPORT_JSON"
import json, sys
search_path, download_path, report_path = sys.argv[1:4]
search = json.load(open(search_path, encoding='utf-8'))
download = json.load(open(download_path, encoding='utf-8'))
results = search.get('results') or []
assert search.get('enabled') is True, search
assert results, search
assert results[0].get('title'), results[0]
assert results[0].get('url'), results[0]
assert download.get('enabled') is True, download
assert int(download.get('size_bytes', 0)) > 0, download
report = {
    'search_query': search.get('query'),
    'top_result': results[0],
    'download': {
        'path': download.get('path'),
        'filename': download.get('filename'),
        'size_bytes': download.get('size_bytes'),
    },
    'status': 'pass',
}
json.dump(report, open(report_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('[ok] local online API search/download checks passed')
print(json.dumps(report, ensure_ascii=False, indent=2))
PY
    fi
  fi
fi

echo "[5/5] Done"
echo "info json: $INFO_JSON"
echo "download path: $DIRECT_DOWNLOAD_PATH"
if [[ -f "$API_REPORT_JSON" ]]; then
  echo "api report: $API_REPORT_JSON"
fi

echo "✅ Online tools / internet check completed"
