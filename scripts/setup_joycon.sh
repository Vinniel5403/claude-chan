#!/bin/bash
# ติดตั้ง venv สำหรับ Joy-Con ไว้ที่ ~/.claude-chan/venv (นอกโฟลเดอร์ plugin -> อัปเดต plugin แล้วไม่หาย)
set -e
HOME_DIR="${CLAUDE_CHAN_HOME:-$HOME/.claude-chan}"
VENV="$HOME_DIR/venv"
mkdir -p "$HOME_DIR"

if command -v uv >/dev/null 2>&1; then
  uv venv --quiet --allow-existing "$VENV"
  uv pip install --quiet --python "$VENV/bin/python" joycon-python hidapi pyglm
else
  python3 -m venv "$VENV"
  "$VENV/bin/python" -m pip install --quiet --upgrade pip
  "$VENV/bin/python" -m pip install --quiet joycon-python hidapi pyglm
fi

"$VENV/bin/python" -c "import pyjoycon, hid" && echo "OK: $VENV"
