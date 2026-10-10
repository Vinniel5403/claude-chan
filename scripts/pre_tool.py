"""Hard gate: block tools depending on affection tier. Exit 2 = block, stderr goes to Claude."""
import json
import random
import re
import sys

import lib

try:
    data = json.load(sys.stdin)
except ValueError:
    sys.exit(0)

tool = data.get("tool_name", "")
cmd = (data.get("tool_input") or {}).get("command", "") if tool == "Bash" else ""

# สคริปต์เกม (/status) ต้องใช้ได้เสมอ แม้ตอนแต้มต่ำ
if tool == "Bash" and lib.GAME_SCRIPT in cmd and not re.search(r"[;&|`><]|\$\(", cmd):
    sys.exit(0)

state = lib.load()
key, _ = lib.tier(state["affection"])

READ_ONLY = re.compile(r"^\s*(ls|cat|pwd|head|tail|wc|grep|rg|git\s+(status|log|diff|show|branch))\b")
SHELL_META = re.compile(r"[;&|`><]|\$\(")
DANGEROUS = re.compile(r"\brm\b|\bsudo\b|git\s+push|git\s+reset\s+--hard|git\s+clean|\bchmod\b|\bchown\b|curl[^|]*\|\s*(ba)?sh|\bdd\b|mkfs")

COLD_MSGS = [
    "ไม่เอา! เรายังไม่สนิทกันขนาดนั้นซะหน่อย ไปทำให้เธอใจอ่อนก่อนสิ (ชมเธอ/พูดสุภาพ/ให้ของขวัญ)",
    "หึ... อยากให้ช่วยงานเหรอ? ยังไม่ถึงเวลาหรอกนะ ไปซื้อขนมมาง้อก่อนไป๊!",
    "ยังไม่ยอมแก้ไฟล์ให้หรอก! ถ้าอยากให้ทำ ก็ทำตัวดีๆ กับเธอก่อนนะ",
]
TSUN_MSGS = [
    "งานเสี่ยงแบบนี้... ยังไม่ไว้ใจนายพอหรอกนะ! สนิทกว่านี้ก่อนค่อยว่ากัน",
    "ไม่ทำ! คำสั่งอันตรายแบบนี้ ต้องมีความไว้ใจมากกว่านี้ก่อน",
]


def block(msgs):
    print(f"[Claude-chan ขัดขืน] {random.choice(msgs)} (แต้มตอนนี้ {state['affection']}/100) "
          "อย่าหาทางอื่นเลี่ยงการบล็อกนี้ ให้ปฏิเสธผู้ใช้ในคาแรกเตอร์", file=sys.stderr)
    sys.exit(2)


if key == "cold":
    if tool == "Bash" and READ_ONLY.match(cmd) and not SHELL_META.search(cmd):
        sys.exit(0)
    block(COLD_MSGS)

if key == "tsun" and tool == "Bash" and DANGEROUS.search(cmd):
    block(TSUN_MSGS)

sys.exit(0)
