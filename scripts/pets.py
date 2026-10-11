"""แปลงการลูบ/เขย่าจาก Joy-Con เป็นแต้ม (daemon เรียก ใส่ state ทันที)"""
import time

import lib

HOUR_CAP = 8          # ลูบได้แต้มรวมสูงสุดต่อชั่วโมง กันนั่งเขย่าฟาร์ม
SHAKE_PENALTY = 2
SHAKE_MAX_PER_BURST = 3


def apply(pets, shakes):
    """ใส่แต้มลง state.json ภายใต้ lock ; คืน (ข้อความ, แต้มปัจจุบัน)"""
    with lib.locked():
        state = lib.load()
        now = time.time()
        hour = state.get("pet_hour") or {"start": 0, "gain": 0}
        if now - hour["start"] > 3600:
            hour = {"start": now, "gain": 0}
        gain = max(0, min(pets, HOUR_CAP - hour["gain"]))
        hour["gain"] += gain
        state["pet_hour"] = hour
        loss = min(shakes, SHAKE_MAX_PER_BURST) * SHAKE_PENALTY
        lib.add(state, gain - loss)
        lib.save(state)

    parts = []
    if pets:
        if gain:
            parts.append("ผู้ใช้ลูบหัวเธอด้วย Joy-Con")
        else:
            parts.append("ผู้ใช้ลูบหัวเธอ แต่ลูบบ่อยเกินไปในชั่วโมงนี้ เธอรู้สึกว่ามากไปแล้ว")
    if shakes:
        parts.append("ผู้ใช้เขย่าตัวเธอแรงๆ เธอตกใจและโกรธ")
    return " และ ".join(parts), state["affection"]
