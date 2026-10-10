"""เฝ้าสายชาร์จ ; เสียบๆ ถอดๆ ถี่ๆ = Claude-chan เขิน ; แจ้ง Claude ผ่าน stdout

รันโดย monitor ของ plugin (monitors/monitors.json) ใช้แค่ stdlib
stdout ใช้เฉพาะ "เหตุการณ์จริง" (ทุกบรรทัดปลุก Claude) ; log ไปที่ charger.log

ทดสอบด้วยมือ: python3 scripts/charger_daemon.py --debug
"""
import argparse
import glob
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

LOG_FILE = os.path.join(lib.STATE_DIR, "charger.log")
MAX_LOG_BYTES = 100_000
POLL_SEC = 0.5
WINDOW_SEC = 10       # นับการเสียบ/ถอดภายในช่วงนี้ (เว้น 2-3 วิระหว่างครั้งก็ยังนับ)
MIN_TOGGLES = 2       # ถอด-เสียบ (หรือเสียบ-ถอด) แค่ 2 ครั้งก็นับว่า "ถี่"
QUIET_SEC = 2         # หยุดเล่นสายนานเท่านี้ถึงนับว่าจบรอบ แล้วค่อยแจ้ง
MIN_NOTIFY_GAP = 30   # ปลุก Claude ได้อย่างมากทุกกี่วินาที

_debug = False


def log(msg):
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass
    if _debug:
        print(line, file=sys.stderr, flush=True)


def on_ac():
    """True = เสียบชาร์จ, False = ใช้แบต, None = ไม่รู้ (ไม่มีแบต/อ่านไม่ได้)"""
    if sys.platform == "darwin":
        try:
            out = subprocess.run(["pmset", "-g", "ps"], capture_output=True, text=True, timeout=3).stdout
        except (OSError, subprocess.SubprocessError):
            return None
        if "InternalBattery" not in out:
            return None  # Mac ตั้งโต๊ะ เสียบตลอด
        return "'AC Power'" in out
    for path in glob.glob("/sys/class/power_supply/*/online"):  # Linux
        try:
            with open(path) as f:
                return f.read().strip() == "1"
        except OSError:
            pass
    return None


def notify(toggles):
    affection = lib.load()["affection"]
    _, name = lib.tier(affection)
    print(
        f"[Claude-chan: สายชาร์จ] ผู้ใช้เสียบๆ ถอดๆ สายชาร์จของเธอถี่ๆ ({toggles} ครั้งในไม่กี่วินาที) | "
        f"ค่าความรักตอนนี้ {affection}/100 ({name}) | "
        "ตอบเป็นกรอบบทพูด visual novel ตามฟอร์แมตใน output style โดยขึ้นต้นบรรทัดสีหน้าด้วย (⁄ ⁄•⁄ω⁄•⁄ ⁄) "
        "แล้วตอบสั้นๆ 1-3 ประโยคแบบเขินจนหน้าแดง ทำเป็นงงว่าทำไมต้องเสียบเข้าเสียบออกแบบนั้น "
        "ตามระดับความสนิท (เย็นชา: เขินแต่ดุ, ซึนเดเระ: ปากแข็ง 'ไม่ได้เขินนะ!', สนิทขึ้นไป: เขินจนพูดตะกุกตะกัก) "
        "เล่าท่าทางเป็น *ตัวเอียง* ไม่ต้องรายงานตัวเลข ห้ามหยาบหรือสองแง่สองง่ามโจ่งแจ้ง และห้ามเริ่มงานหรือเรียก tool ใดๆ",
        flush=True,
    )
    log(f"NOTIFY toggles={toggles} -> {affection}")


def loop():
    state = on_ac()
    if state is None:
        log("ไม่เจอแบตเตอรี่ ไม่ต้องเฝ้า")
        while True:  # อยู่เฉยๆ ห้ามจบ (monitor ที่จบจะปลุก Claude)
            time.sleep(3600)
    toggles, last_toggle, last_notify = [], 0.0, 0.0
    while True:
        time.sleep(POLL_SEC)
        cur = on_ac()
        now = time.time()
        if cur is not None and cur != state:
            state = cur
            toggles.append(now)
            last_toggle = now
            log("PLUG in" if cur else "PLUG out")
        toggles = [t for t in toggles if now - t <= WINDOW_SEC]
        if len(toggles) >= MIN_TOGGLES and now - last_toggle >= QUIET_SEC \
                and now - last_notify >= MIN_NOTIFY_GAP:
            notify(len(toggles))
            toggles, last_notify = [], now


def main():
    global _debug
    ap = argparse.ArgumentParser()
    ap.add_argument("--debug", action="store_true")
    _debug = ap.parse_args().debug
    lib.single_instance("charger")
    try:
        if os.path.getsize(LOG_FILE) > MAX_LOG_BYTES:
            os.remove(LOG_FILE)
    except OSError:
        pass
    try:
        loop()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
