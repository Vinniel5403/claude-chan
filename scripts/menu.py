"""เมนู ▸ [Y] [B] [A] ท้ายคำตอบ : ใช้ร่วมกันระหว่าง prompt_submit (พิมพ์ตัวอักษร) และ joycon_daemon (กดปุ่ม Y/B/A)

Stop hook เก็บเมนูของคำตอบล่าสุดไว้ใน MENU_FILE ; daemon หยิบไปใช้ตอนกดปุ่ม (หยิบแล้วลบ กดซ้ำไม่นับ)
"""
import json
import os
import re

import game
import lib

MENU_FILE = os.path.join(lib.STATE_DIR, "menu.json")
KEYS = "YBA"  # ลำดับในเมนู ; ตรงกับปุ่มบน Joy-Con (R)
MENU_LINE = re.compile(r"▸\s*(\[[YAB123]\].*)")
ITEM = re.compile(r"\[([YAB123])\]\s*([^\[]*)")
TRIP_KW = re.compile(r"เที่ยว|พาไป|ชวนไป|ไปกัน|ไป(?=\S)")
GIFT_KW = re.compile(r"ของขวัญ|ซื้อ|เลี้ยง|มอบ|ให้(?=\S)")


def parse(text):
    """ข้อความคำตอบ -> {"Y": …, "B": …, "A": …} หรือ None

    จับคู่ตามตัวอักษร (Claude เรียงผิดก็ยังถูกปุ่ม) ; [1][2][3] = ฟอร์แมตเก่า เทียบตามตำแหน่ง
    """
    lines = MENU_LINE.findall(text or "")
    if not lines:
        return None
    items = ITEM.findall(lines[-1])
    menu = {k if k in KEYS else KEYS["123".index(k)]: v.strip() for k, v in items}
    return menu if len(items) == 3 and len(menu) == 3 else None


def _text(msg):
    content = (msg.get("message") or {}).get("content")
    if isinstance(content, str):
        return content
    return "".join(b.get("text", "") for b in content or [] if isinstance(b, dict))


def last_menu(path):
    """เมนู 3 ข้อที่ Claude เสนอไว้ในคำตอบล่าสุด (เมนูเปลี่ยนตามบทสนทนา) -> {"Y": …, "B": …, "A": …} หรือ None"""
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


def pick(state, key, picked, rest=""):
    """เลือกข้อ Y/B/A -> (action, emotion, delta) หรือ None ; ใส่แต้มลง state แล้ว (ผู้เรียกต้องถือ lock และ save เอง)"""
    if picked:
        if TRIP_KW.search(picked):
            res = game.trip(state, rest or picked)
        elif GIFT_KW.search(picked):
            res = game.gift(state, rest or picked)
        else:
            return f"ผู้ใช้เลือกตัวเลือก [{key}] จากเมนูที่คุณเสนอ: {picked} (เล่นต่อตามนั้น แต้มไม่เปลี่ยน)", None, 0
    else:
        # ไม่รู้เมนูเดิม: ใช้เมนูคลาสสิก (A เที่ยว, B ของขวัญ)
        if key == "Y":
            return None
        res = (game.trip if key == "A" else game.gift)(state, rest)
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
    """daemon: หยิบเมนูที่รออยู่ (หยิบแล้วลบ) -> dict หรือ None"""
    try:
        with open(MENU_FILE, encoding="utf-8") as f:
            menu = json.load(f)
    except (OSError, ValueError):
        return None
    clear()
    return menu if isinstance(menu, dict) and set(menu) == set(KEYS) else None
