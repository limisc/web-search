#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"

usage() {
  cat <<'EOF'
Usage:
  scripts/local_service.sh start [live|preview] [port]
  scripts/local_service.sh stop [live|preview]
  scripts/local_service.sh status [live|preview]
  scripts/local_service.sh restart [live|preview] [port]

Environment overrides:
  WEB_SEARCH_RUNTIME_DIR  Runtime directory root. Default: <repo>/.runtime
  HOST                    HTTP bind host. Default: 127.0.0.1
  PATH_MCP                MCP mount path. Default: /mcp
  PORT                    Overrides the selected port.
EOF
}

command="${1:-}"
name="${2:-live}"
requested_port="${3:-}"

if [[ -z "$command" ]]; then
  usage
  exit 1
fi

case "$name" in
  live) default_port=8000 ;;
  preview) default_port=8001 ;;
  *)
    echo "Unknown service name: $name" >&2
    usage
    exit 1
    ;;
esac

runtime_dir="${WEB_SEARCH_RUNTIME_DIR:-$repo_root/.runtime}"
tmp_dir="$runtime_dir/tmp"
host="${HOST:-127.0.0.1}"
path_mcp="${PATH_MCP:-/mcp}"
port="${PORT:-${requested_port:-$default_port}}"
log_file="$runtime_dir/$name.log"
pid_file="$runtime_dir/$name.pid"

mkdir -p "$runtime_dir" "$tmp_dir"

pid_if_running() {
  if [[ ! -f "$pid_file" ]]; then
    return 1
  fi

  local pid
  pid="$(cat "$pid_file")"
  if [[ -z "$pid" ]]; then
    return 1
  fi

  if kill -0 "$pid" 2>/dev/null; then
    printf '%s\n' "$pid"
    return 0
  fi

  rm -f "$pid_file"
  return 1
}

start_service() {
  local existing_pid
  if existing_pid="$(pid_if_running)"; then
    echo "$name already running pid=$existing_pid"
    echo "log=$log_file"
    echo "tmp=$tmp_dir"
    return 0
  fi

  cd "$repo_root"
  : > "$log_file"
  TMPDIR="$tmp_dir" nohup uv run python -m web_search.app \
    --transport http \
    --host "$host" \
    --port "$port" \
    --path "$path_mcp" \
    >> "$log_file" 2>&1 &
  local pid=$!
  echo "$pid" > "$pid_file"

  sleep 1
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "Failed to start $name service" >&2
    tail -n 40 "$log_file" >&2 || true
    rm -f "$pid_file"
    exit 1
  fi

  echo "started $name pid=$pid"
  echo "url=http://$host:$port"
  echo "mcp=http://$host:$port$path_mcp"
  echo "log=$log_file"
  echo "pid_file=$pid_file"
  echo "tmp=$tmp_dir"
}

stop_service() {
  local pid
  if ! pid="$(pid_if_running)"; then
    echo "$name not running"
    return 0
  fi

  kill "$pid" 2>/dev/null || true
  for _ in $(seq 1 20); do
    if ! kill -0 "$pid" 2>/dev/null; then
      rm -f "$pid_file"
      echo "stopped $name pid=$pid"
      return 0
    fi
    sleep 0.25
  done

  kill -9 "$pid" 2>/dev/null || true
  rm -f "$pid_file"
  echo "killed $name pid=$pid"
}

status_service() {
  local pid
  if pid="$(pid_if_running)"; then
    echo "$name running pid=$pid"
    echo "url=http://$host:$port"
    echo "mcp=http://$host:$port$path_mcp"
    echo "log=$log_file"
    echo "pid_file=$pid_file"
    echo "tmp=$tmp_dir"
    return 0
  fi

  echo "$name not running"
  echo "log=$log_file"
  echo "pid_file=$pid_file"
  echo "tmp=$tmp_dir"
}

case "$command" in
  start)
    start_service
    ;;
  stop)
    stop_service
    ;;
  status)
    status_service
    ;;
  restart)
    stop_service
    start_service
    ;;
  *)
    echo "Unknown command: $command" >&2
    usage
    exit 1
    ;;
esac
