import json
import re
import sys
import time

import lib
import menu
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

# Y / [Y] / 1 (เลขแบบเก่า = ตามตำแหน่งในเมนู) ; ตัวพิมพ์เล็กไม่นับ กัน "y" ตอบ yes หรือประโยคอังกฤษขึ้นต้นด้วย "a"
MENU = re.compile(r"^\s*\[?([YAB123])\]?(?:\s+(.*))?$", re.S)


with lib.locked():
    state = lib.load()
    days = lib.apply_decay(state)
    prompt = data.get("prompt", "")
    action = emotion = None
    delta = 0

    m = MENU.match(prompt)
    if m:
        key, rest = m.group(1), (m.group(2) or "").strip()
        key = menu.KEYS["123".index(key)] if key.isdigit() else key
        menu_items = menu.last_menu(data.get("transcript_path"))
        picked = menu_items[key] if menu_items else ""
        if len(rest) <= 30:
            action, emotion, delta = menu.pick(state, key, picked, rest) or (None, None, 0)

    if action is None:
        delta = score(prompt, state)
        if delta:
            lib.add(state, delta)
    lib.save(state)
menu.clear()  # ผู้ใช้พิมพ์แล้ว เมนูเก่าใช้กับปุ่ม Joy-Con ไม่ได้อีก

print(json.dumps({
    "systemMessage": sprites.render(state, delta, emotion, days, prompt),
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": persona.build(state, delta=delta, days_away=days, action=action),
    }
}, ensure_ascii=False))
sys.exit(0)
