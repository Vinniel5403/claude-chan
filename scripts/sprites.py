"""โหลดสไปรต์ ASCII จาก sprites/*.txt แล้วเลือกตามอารมณ์"""
import os

import lib

SPRITE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sprites")


def pick(state, delta=0):
    """เลือกอารมณ์จากสิ่งที่เพิ่งเกิด แล้วค่อยตกไปที่ tier"""
    if delta < 0:
        return "angry"
    if delta >= 3:
        return "blush"
    key, _ = lib.tier(state["affection"])
    return {"cold": "sulk", "tsun": "normal", "close": "normal", "love": "happy"}[key]


def render(state, delta=0, emotion=None):
    name = emotion or pick(state, delta)
    try:
        with open(os.path.join(SPRITE_DIR, f"{name}.txt"), encoding="utf-8") as f:
            art = f.read().rstrip("\n")
    except OSError:
        return ""
    a = state["affection"]
    return f"{art}\n[{lib.hearts(a)} {lib.tier(a)[1]} {a}/100]"
