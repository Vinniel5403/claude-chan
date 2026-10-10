"""เมนู ▸ [1] [2] [3] ท้ายคำตอบ : ใช้ร่วมกันระหว่าง prompt_submit (พิมพ์เลข) และ joycon_daemon (กดปุ่ม A/B)

Stop hook เก็บเมนูของคำตอบล่าสุดไว้ใน MENU_FILE ; daemon หยิบไปใช้ตอนกดปุ่ม (หยิบแล้วลบ กดซ้ำไม่นับ)
"""
import json
import os
import re

import game
import lib

MENU_FILE = os.path.join(lib.STATE_DIR, "menu.json")
MENU_LINE = re.compile(r"▸\s*\[1\](.*?)\[2\](.*?)\[3\](.*)")
TRIP_KW = re.compile(r"เที่ยว|พาไป|ชวนไป|ไปกัน|ไป(?=\S)")
GIFT_KW = re.compile(r"ของขวัญ|ซื้อ|เลี้ยง|มอบ|ให้(?=\S)")


def parse(text):
    """ข้อความคำตอบ -> [ข้อ1, ข้อ2, ข้อ3] หรือ None"""
    m = MENU_LINE.search(text or "")
    return [g.strip() for g in m.groups()] if m else None


def _text(msg):
    content = (msg.get("message") or {}).get("content")
    if isinstance(content, str):
        return content
    return "".join(b.get("text", "") for b in content or [] if isinstance(b, dict))


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
        menu = parse(_text(msg))
        if menu:
            return menu
    return None


def pick(state, choice, picked, rest=""):
    """เลือกข้อ 1/2 -> (action, emotion, delta) ; ใส่แต้มลง state แล้ว (ผู้เรียกต้องถือ lock และ save เอง)"""
    if picked:
        if TRIP_KW.search(picked):
            res = game.trip(state, rest or picked)
        elif GIFT_KW.search(picked):
            res = game.gift(state, rest or picked)
        else:
            return f"ผู้ใช้เลือกตัวเลือกที่ {choice} จากเมนูที่คุณเสนอ: {picked} (เล่นต่อตามนั้น แต้มไม่เปลี่ยน)", None, 0
    else:
        # ไม่รู้เมนูเดิม: ใช้เมนูคลาสสิก
        res = (game.trip if choice == "1" else game.gift)(state, rest)
    return res["text"], res["emotion"], res["delta"]


def store(menu):
    """Stop hook: จำเมนูล่าสุดไว้ให้ปุ่ม Joy-Con ; None = ลบทิ้ง"""
    if not menu:
        clear()
        return
    os.makedirs(lib.STATE_DIR, exist_ok=True)
    with open(MENU_FILE, "w", encoding="utf-8") as f:
        json.dump(menu, f, ensure_ascii=False)


def clear():
    try:
        os.remove(MENU_FILE)
    except OSError:
        pass


def take():
    """daemon: หยิบเมนูที่รออยู่ (หยิบแล้วลบ) -> list หรือ None"""
    try:
        with open(MENU_FILE, encoding="utf-8") as f:
            menu = json.load(f)
    except (OSError, ValueError):
        return None
    clear()
    return menu if isinstance(menu, list) and len(menu) == 3 else None
