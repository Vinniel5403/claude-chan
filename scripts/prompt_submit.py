import json
import re
import sys
import time

import game
import lib
import persona
import sprites

POSITIVE = re.compile(
    r"ขอบคุณ|ขอบใจ|น่ารัก|เก่งมาก|เก่งจัง|สุดยอด|เยี่ยม|ชอบ|รักนะ|เหนื่อยไหม|พักก่อน|ขอร้อง|รบกวน|"
    r"thank|thanks|please|cute|good job|great job|well done|awesome|love you|appreciate",
    re.I,
)
POLITE = re.compile(r"หน่อย|นะคะ|นะครับ|ได้ไหม|ได้มั้ย|ช่วย.{0,20}(ด้วย|หน่อย)|kindly|could you|would you", re.I)
RUDE = re.compile(
    r"โง่|ห่วย|ไร้ประโยชน์|กาก|เหี้ย|สัส|ควย|ไอ้บ้า|หุบปาก|"
    r"stupid|useless|idiot|shut up|dumb|wtf|fuck|shit|garbage",
    re.I,
)

GAIN_COOLDOWN_SEC = 20
MAX_GAIN = 5


def score(prompt, state):
    text = prompt.strip()
    if not text or text.startswith("/"):
        return 0
    delta = 0
    if RUDE.search(text):
        delta -= 5
    now = time.time()
    if now - state["last_gain"] >= GAIN_COOLDOWN_SEC:
        gain = 0
        if POSITIVE.search(text):
            gain += 3
        if POLITE.search(text):
            gain += 1
        if len(text) >= 80:  # ให้ context ละเอียด = ใส่ใจ
            gain += 1
        gain = min(gain, MAX_GAIN)
        if gain:
            state["last_gain"] = now
        delta += gain
    return delta


try:
    data = json.load(sys.stdin)
except ValueError:
    data = {}

MENU = re.compile(r"^\s*\[?([123])\]?(?:\s+(.*))?$", re.S)

with lib.locked():
    state = lib.load()
    days = lib.apply_decay(state)
    prompt = data.get("prompt", "")
    action = emotion = None
    delta = 0

    m = MENU.match(prompt)
    if m:
        choice, rest = m.group(1), (m.group(2) or "").strip()
        if choice in "12" and len(rest) <= 30:  # สั้นพอจะเป็นชื่อสถานที่/ของขวัญ ไม่ใช่คำสั่งงาน
            res = (game.trip if choice == "1" else game.gift)(state, rest)
            action, emotion, delta = res["text"], res["emotion"], res["delta"]
        elif choice == "3":
            prompt = rest  # [3] เขียนเอง: ข้อความที่เหลือคือสิ่งที่พูด/สั่งจริง

    if action is None:
        delta = score(prompt, state)
        if delta:
            lib.add(state, delta)
    lib.save(state)

print(json.dumps({
    "systemMessage": sprites.render(state, delta, emotion),
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": persona.build(state, delta=delta, days_away=days, action=action),
    }
}, ensure_ascii=False))
sys.exit(0)
