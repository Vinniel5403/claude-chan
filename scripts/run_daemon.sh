#!/bin/bash
# เรียกโดย monitors/monitors.json ; ไม่มี .venv ก็จบเงียบๆ (ไม่ปลุก Claude ด้วย error)
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || exit 0
exec "$PY" "$ROOT/scripts/joycon_daemon.py" "$@"
