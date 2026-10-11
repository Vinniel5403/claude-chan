"""Bash จบแล้ว : เทสต์ผ่าน / commit สำเร็จ = ดีใจ ; พังติดกัน 3 ครั้ง = ปลอบ (แค่เปลี่ยนอารมณ์ ไม่ให้แต้ม กันปั๊มแต้ม)

PostToolUse = คำสั่งสำเร็จ ; PostToolUseFailure = exit code ไม่ใช่ 0 (Claude Code ถือว่า tool error)
"""
import json
import random
import re
import sys
import time

import greet
import lib
import sprites

TEST = re.compile(
    r"\b(pytest|unittest|jest|vitest|rspec|(npm|yarn|pnpm|bun)\s+(run\s+)?test|(go|cargo|deno|mix|dotnet)\s+test|make\s+test)\b"
)
COMMIT = re.compile(r"\bgit\s+commit\b")
# exit 1 ของพวกนี้เป็นเรื่องปกติ (grep ไม่เจอ, test -f ไม่มีไฟล์) ไม่นับว่าพัง
IGNORE = re.compile(r"^\s*(ls|cat|pwd|head|tail|wc|grep|rg|find|which|test|\[|diff|git\s+(status|log|diff|show|branch))\b")
FAIL_STREAK = 3
COOLDOWN_SEC = 120  # สไปรต์ใหญ่ โชว์ถี่แล้วรก

LINES = {
    "test": {
        "cold": ["...ผ่านแล้วเหรอ ก็ดี"],
        "tsun": ["เทสต์ผ่าน... ก็ไม่ได้แย่นี่ ฮึ่ม", "ผ่านแล้วก็อย่าเพิ่งได้ใจล่ะ!"],
        "close": ["เย้ เทสต์ผ่านแล้ว~ เก่งมากเลย", "เขียวหมดเลย! ไปต่อกันน้า"],
        "love": ["เทสต์ผ่านหมดเลย! เก่งที่สุดเลยน้า 💕", "เขียวทั้งแผงเลย~ เค้าภูมิใจในตัวเธอจัง"],
    },
    "commit": {
        "cold": ["...อืม commit แล้ว"],
        "tsun": ["commit แล้วเหรอ ก-ก็ทำได้ดีนี่", "เก็บงานเป็นด้วยแฮะ... ไม่ได้ชมนะ!"],
        "close": ["commit เรียบร้อย~ ไปต่อกันเลย", "เก็บงานแล้ว เหนื่อยไหม~"],
        "love": ["commit แล้ว! เก็บความทรงจำของเราไว้อีกชิ้นนะ 💕", "เรียบร้อย~ เค้าจดไว้ในใจแล้วนะว่าวันนี้เธอขยันแค่ไหน"],
    },
    "fail": {
        "cold": ["พังซ้ำๆ อยู่นั่น... ก็ไม่ได้สนใจหรอก"],
        "tsun": ["พังอีกแล้วเหรอ! ซุ่มซ่ามจริง... ฮึ่ม จะช่วยดูให้ก็ได้", "นี่มันกี่รอบแล้วเนี่ย! ใจเย็นๆ ก่อนสิ"],
        "close": ["พังอีกแล้ว... พักหายใจแป๊บนึงก่อนนะ", "ไม่เป็นไรน้า ค่อยๆ ไล่ดูไปด้วยกัน"],
        "love": ["พังติดกันเลย... ไม่เป็นไรนะ เค้าอยู่ข้างๆ เสมอ 🥺", "อย่าเพิ่งท้อนะ เดี๋ยวเค้าช่วยหาจุดพังให้เอง"],
    },
}
EMOTION = {
    "test": {"cold": "normal", "tsun": "shy", "close": "happy", "love": "love"},
    "commit": {"cold": "normal", "tsun": "shy", "close": "happy", "love": "love"},
    "fail": {"cold": "sulk", "tsun": "sulk", "close": "cry", "love": "cry"},
}
WHAT = {
    "test": "เทสต์ผ่าน",
    "commit": "git commit สำเร็จ",
    "fail": f"คำสั่งพังติดกัน {FAIL_STREAK} ครั้ง",
}

try:
    data = json.load(sys.stdin)
except ValueError:
    sys.exit(0)

cmd = (data.get("tool_input") or {}).get("command", "")
failed = data.get("hook_event_name") == "PostToolUseFailure"
if not cmd or IGNORE.match(cmd) or data.get("is_interrupt"):  # ผู้ใช้กดยกเลิกเอง ไม่ใช่พัง
    sys.exit(0)

with lib.locked():
    state = lib.load()
    event = None
    if failed:
        state["fail_streak"] = state.get("fail_streak", 0) + 1
        if state["fail_streak"] >= FAIL_STREAK:
            event = "fail"
    else:
        state["fail_streak"] = 0
        if TEST.search(cmd):
            event = "test"
        elif COMMIT.search(cmd):
            event = "commit"
    if event and time.time() - state.get("last_react", 0) < COOLDOWN_SEC:
        event = None
    if event:
        state["last_react"] = time.time()
        if event == "fail":
            state["fail_streak"] = 0  # ปลอบแล้ว นับใหม่
    lib.save(state)

if not event:
    sys.exit(0)

key, _ = lib.tier(state["affection"])
line = random.choice(LINES[event][key])
print(json.dumps({
    "systemMessage": sprites.render(state, emotion=EMOTION[event][key]) + "\n\n" + greet.box(line),
    "hookSpecificOutput": {
        "hookEventName": data.get("hook_event_name", "PostToolUse"),
        "additionalContext": (
            f"[Claude-chan เห็นผลคำสั่ง] {WHAT[event]} ผู้ใช้เห็นรูปและบทพูดนี้ไปแล้ว: 「{line}」 "
            "ทำงานต่อตามปกติ ถ้าจะพูดถึงในคำตอบให้ต่อเนื่องจากบทพูดนี้ ไม่ต้องพูดซ้ำ"
        ),
    },
}, ensure_ascii=False))
sys.exit(0)
