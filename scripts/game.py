"""Game actions. ใช้จาก prompt_submit (เมนู [1] [2]) และ CLI: game.py status"""
import datetime
import random
import sys
import time

import lib

TRIP_COOLDOWN = 1800
GIFT_COOLDOWN = 300
PLACES = ["สวนสนุก", "ทะเล", "คาเฟ่แมว", "พิพิธภัณฑ์", "งานเทศกาล", "ดาดฟ้าดูดาว"]
GIFTS = ["ชานมไข่มุก", "เค้กสตรอว์เบอร์รี", "ตุ๊กตาหมี", "ช่อดอกไม้", "ช็อกโกแลต", "โมจิไดฟุกุ"]


def _fav(pool):
    """ของโปรดเปลี่ยนทุกวัน"""
    return pool[datetime.date.today().toordinal() % len(pool)]


def _left(last, cd):
    return max(0, int(cd - (time.time() - last)))


def trip(state, place=""):
    """[1] พาไปเที่ยว -> dict(ok, delta, emotion, text)"""
    left = _left(state["last_trip"], TRIP_COOLDOWN)
    if left:
        return {"ok": False, "delta": 0, "emotion": None,
                "text": f"พาไปเที่ยวถี่เกินไป เธอยังเหนื่อยจากครั้งก่อน (รออีก {left // 60 + 1} นาที) แต้มไม่เปลี่ยน"}
    place = place.strip() or random.choice(PLACES)
    liked = _fav(PLACES) in place
    delta = 10 if liked else 6
    lib.add(state, delta)
    state["last_trip"] = time.time()
    return {"ok": True, "delta": delta, "emotion": "happy",
            "text": f"พาไปเที่ยว: {place} ผลลัพธ์: {'ที่โปรดของเธอวันนี้เป๊ะ ดีใจมาก' if liked else 'สนุกดี'} (แต้ม +{delta})"}


def gift(state, item=""):
    """[2] ให้ของขวัญ -> dict(ok, delta, emotion, text)"""
    left = _left(state["last_gift"], GIFT_COOLDOWN)
    if left:
        return {"ok": False, "delta": 0, "emotion": None,
                "text": f"ให้ของขวัญติดกัน เธอรู้สึกว่าโดนซื้อใจ (รออีก {left} วินาที) แต้มไม่เปลี่ยน"}
    item = item.strip() or random.choice(GIFTS)
    liked = _fav(GIFTS) in item
    delta = 8 if liked else 4
    lib.add(state, delta)
    state["last_gift"] = time.time()
    return {"ok": True, "delta": delta, "emotion": "blush",
            "text": f"ให้ของขวัญ: {item} ผลลัพธ์: {'ของโปรดวันนี้ตรงเป๊ะ ดีใจมาก' if liked else 'ชอบนะ'} (แต้ม +{delta})"}


if __name__ == "__main__":
    if sys.argv[1:] == ["status"]:
        s = lib.load()
        a = s["affection"]
        print(f"ค่าความรัก: {a}/100 {lib.hearts(a)} ({lib.tier(a)[1]})")
    else:
        print("usage: game.py status")
        sys.exit(1)
