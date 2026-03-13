#!/data/data/com.termux/files/usr/bin/bash
# Проверка целостности git-дерева и видимости backend в GitHub для ветки work.

set -euo pipefail

REPO_ROOT="${1:-$HOME/roampal-android}"
BRANCH="${2:-work}"

cd "$REPO_ROOT"

echo "== Repo integrity check =="
echo "repo: $REPO_ROOT"
echo "branch: $BRANCH"

echo "[1/4] Local git tree backend files"
LOCAL_BACKEND_COUNT=$(git ls-tree -r --name-only "$BRANCH" | grep '^backend/' | wc -l | tr -d ' ')
git ls-tree -r --name-only "$BRANCH" | grep '^backend/' | sed -n '1,40p'
echo "local backend file count: $LOCAL_BACKEND_COUNT"

echo "[2/4] Local tracked files count"
LOCAL_TOTAL=$(git ls-tree -r --name-only "$BRANCH" | wc -l | tr -d ' ')
echo "local total files count: $LOCAL_TOTAL"

echo "[3/4] Remote branch head"
git fetch origin "$BRANCH" >/dev/null
LOCAL_HEAD=$(git rev-parse "$BRANCH")
REMOTE_HEAD=$(git rev-parse "origin/$BRANCH")
echo "local head:  $LOCAL_HEAD"
echo "remote head: $REMOTE_HEAD"
if [ "$LOCAL_HEAD" != "$REMOTE_HEAD" ]; then
  echo "WARN: local/remote heads differ"
fi

echo "[4/4] GitHub API visibility check"
curl -fsSL "https://api.github.com/repos/Wvwvwvwvwv/jubilant-computing-machine/contents/backend?ref=$BRANCH" \
  | python -c 'import json,sys; arr=json.load(sys.stdin); print("backend dirs:", [x["name"] for x in arr])'

curl -fsSL "https://api.github.com/repos/Wvwvwvwvwv/jubilant-computing-machine/git/trees/$BRANCH?recursive=1" \
  | python -c 'import json,sys; j=json.load(sys.stdin); paths=[x["path"] for x in j.get("tree",[]) if x.get("type")=="blob" and x.get("path","").startswith("backend/")]; print("github backend blob count:", len(paths)); print("sample:", paths[:20])'

echo "✅ integrity check completed"
