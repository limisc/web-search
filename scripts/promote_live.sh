#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
live_root="${LIVE_WORKTREE_PATH:-$repo_root/../web-search-live}"
service_script="$live_root/scripts/local_service.sh"
commitish="${1:-HEAD}"
skip_checks="${SKIP_CHECKS:-0}"

usage() {
  cat <<'EOF'
Usage:
  scripts/promote_live.sh [commitish]

Defaults:
  commitish defaults to HEAD from the current checkout

Environment:
  LIVE_WORKTREE_PATH  Override live worktree path
  SKIP_CHECKS=1       Skip pytest, ruff, and pyright in dev before promotion
EOF
}

if [[ "$commitish" == "-h" || "$commitish" == "--help" ]]; then
  usage
  exit 0
fi

if [[ ! -d "$live_root/.git" && ! -f "$live_root/.git" ]]; then
  echo "Live worktree not found: $live_root" >&2
  echo "Create it first with: git worktree add --detach ../web-search-live HEAD" >&2
  exit 1
fi

if [[ ! -x "$service_script" ]]; then
  echo "Missing live service script: $service_script" >&2
  exit 1
fi

cd "$repo_root"
resolved_commit="$(git rev-parse "$commitish")"
short_commit="$(git rev-parse --short "$resolved_commit")"
current_branch="$(git branch --show-current || true)"

echo "dev repo=$repo_root"
echo "dev branch=${current_branch:-detached}"
echo "promoting commit=$short_commit"
echo "live repo=$live_root"

if [[ "$skip_checks" != "1" ]]; then
  echo
  echo "Running dev checks"
  uv run pytest -q
  uv run ruff check .
  uv run pyright
fi

echo

echo "Stopping live service"
"$service_script" stop live

echo

echo "Updating live worktree"
cd "$live_root"
git fetch "$repo_root" "$resolved_commit"
git checkout --detach FETCH_HEAD

echo

echo "Syncing live environment"
uv sync --extra dev

echo

echo "Starting live service"
"$service_script" start live

echo

echo "Live status"
"$service_script" status live

echo

echo "Promoted live to $short_commit"
