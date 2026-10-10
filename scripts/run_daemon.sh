#!/bin/bash
# เรียกโดย monitors/monitors.json ; ไม่มี venv ก็อยู่เฉยๆ (ห้ามจบ: monitor ที่จบจะปลุก Claude ให้ตอบ)
# หา venv ที่ ~/.claude-chan/venv (จาก setup_joycon.sh) ก่อน แล้วค่อย .venv ใน repo (ตอน dev)
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOME_DIR="${CLAUDE_CHAN_HOME:-$HOME/.claude-chan}"
for PY in "$HOME_DIR/venv/bin/python" "$ROOT/.venv/bin/python"; do
  [ -x "$PY" ] && exec "$PY" "$ROOT/scripts/joycon_daemon.py" "$@"
done
while :; do sleep 86400; done
