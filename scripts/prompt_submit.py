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
MENU_LINE = re.compile(r"▸\s*\[1\](.*?)\[2\](.*?)\[3\](.*)")
TRIP_KW = re.compile(r"เที่ยว|พาไป|ชวนไป|ไปกัน|ไป(?=\S)")
GIFT_KW = re.compile(r"ของขวัญ|ซื้อ|เลี้ยง|มอบ|ให้(?=\S)")


def last_menu(path):
    """เมนู 3 ข้อที่ Claude เสนอไว้ในคำตอบล่าสุด (เมนูเปลี่ยนตามบทสนทนา) -> [ข้อ1, ข้อ2, ข้อ3] หรือ None"""
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()[-200:]
    except (OSError, TypeError):
        return None
    for raw in reversed(lines):
        try:
            msg = json.loads(raw)
        except ValueError:
            continue
        if msg.get("type") != "assistant":
            continue
        content = (msg.get("message") or {}).get("content")
        text = content if isinstance(content, str) else "".join(
            b.get("text", "") for b in content or [] if isinstance(b, dict))
        m = MENU_LINE.search(text)
        if m:
            return [g.strip() for g in m.groups()]
    return None


with lib.locked():
    state = lib.load()
    days = lib.apply_decay(state)
    prompt = data.get("prompt", "")
    action = emotion = None
    delta = 0

    m = MENU.match(prompt)
    if m:
        choice, rest = m.group(1), (m.group(2) or "").strip()
        menu = last_menu(data.get("transcript_path"))
        picked = menu[int(choice) - 1] if menu else ""
        if choice == "3":
            prompt = rest or prompt  # [3] เขียนเอง: ข้อความที่เหลือคือสิ่งที่พูด/สั่งจริง
        elif picked and len(rest) <= 30:
            if TRIP_KW.search(picked):
                res = game.trip(state, rest or picked)
            elif GIFT_KW.search(picked):
                res = game.gift(state, rest or picked)
            else:
                res = None
            if res:
                action, emotion, delta = res["text"], res["emotion"], res["delta"]
            else:
                action = f"ผู้ใช้เลือกตัวเลือกที่ {choice} จากเมนูที่คุณเสนอ: {picked} (เล่นต่อตามนั้น แต้มไม่เปลี่ยน)"
        elif not picked:
            # ไม่รู้เมนูเดิม: ใช้เมนูคลาสสิก
            res = (game.trip if choice == "1" else game.gift)(state, rest) if len(rest) <= 30 else None
            if res:
                action, emotion, delta = res["text"], res["emotion"], res["delta"]

    if action is None:
        delta = score(prompt, state)
        if delta:
            lib.add(state, delta)
    lib.save(state)

print(json.dumps({
    "systemMessage": sprites.render(state, delta, emotion, days, prompt),
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": persona.build(state, delta=delta, days_away=days, action=action),
    }
}, ensure_ascii=False))
sys.exit(0)
