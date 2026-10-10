"""โหลดสไปรต์ ASCII จาก sprites/*.txt แล้วเลือกตามอารมณ์"""
import os
import time

import lib

SPRITE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sprites")


def pick(state, delta=0, days=0, prompt=""):
    """เลือกอารมณ์จากสิ่งที่เพิ่งเกิด แล้วค่อยตกไปที่ tier ; ถ้าไม่มีไฟล์ของอารมณ์นั้นจะถอยไปอารมณ์พื้นฐาน"""
    a = state["affection"]
    key, _ = lib.tier(a)
    base = {"cold": "sulk", "tsun": "normal", "close": "normal", "love": "happy"}[key]
    if delta < 0:
        want = ["angry"]
    elif a < 10:
        want = ["cry"]
    elif days >= 2:
        want = ["sad"]
    elif delta >= 5 or a >= 100:
        want = ["love", "blush"]
    elif delta >= 4 and key == "tsun":
        want = ["shy", "blush"]
    elif delta >= 3:
        want = ["blush"]
    elif 3 <= time.localtime().tm_hour < 5:
        want = ["sleepy"]
    elif len(prompt) >= 80:
        want = ["think"]
    else:
        want = []
    for name in want + [base]:
        if os.path.exists(os.path.join(SPRITE_DIR, f"{name}.txt")):
            return name
    return "normal"


def render(state, delta=0, emotion=None, days=0, prompt=""):
    name = emotion or pick(state, delta, days, prompt)
    try:
        with open(os.path.join(SPRITE_DIR, f"{name}.txt"), encoding="utf-8") as f:
            art = f.read().rstrip("\n")
    except OSError:
        return ""
    a = state["affection"]
    return f"\n{art}\n[{lib.hearts(a)} {lib.tier(a)[1]} {a}/100]"
