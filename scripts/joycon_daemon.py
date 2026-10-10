"""อ่าน Joy-Con (R) ผ่าน Bluetooth ; ตรวจลูบ/เขย่า ; ใส่แต้มทันที ; แจ้ง Claude ผ่าน stdout

รันโดย monitor ของ plugin (monitors/monitors.json) : ทุกบรรทัดที่ print ออก stdout
จะกลายเป็นการแจ้งเตือนที่ปลุก Claude ให้ตอบ ดังนั้น stdout ใช้เฉพาะ "เหตุการณ์จริง"
ส่วน log ทั่วไปไปที่ joycon.log เท่านั้น

ทดสอบด้วยมือ: .venv/bin/python scripts/joycon_daemon.py --debug
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import pet_detect  # noqa: E402
import pets  # noqa: E402

RAW_PER_G = 4096.0
LOG_FILE = os.path.join(lib.STATE_DIR, "joycon.log")
PID_FILE = os.path.join(lib.STATE_DIR, "joycon.pid")
MAX_LOG_BYTES = 200_000
QUIET_SEC = 2.5       # หยุดลูบนานเท่านี้ถึงนับว่าจบรอบ แล้วค่อยแจ้ง Claude
MIN_NOTIFY_GAP = 20   # ปลุก Claude ได้อย่างมากทุกกี่วินาที (แต่ละครั้งคือ 1 turn ที่เสียโทเคน)

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


def notify(line):
    """บรรทัดเดียว = 1 notification ถึง Claude"""
    print(line, flush=True)


def already_running():
    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        if pid != os.getpid():
            os.kill(pid, 0)
            return True
    except (OSError, ValueError):
        pass
    return False


FACES = {"pet": "(⁄ ⁄>⁄ ▽ ⁄<⁄ ⁄)", "shake": "(`Д´#)"}


def flush(pending):
    text, affection = pets.apply(pending["pet"], pending["shake"])
    face = FACES["shake" if pending["shake"] else "pet"]
    key, name = lib.tier(affection)
    notify(
        f"[Claude-chan: สัมผัสจาก Joy-Con] {text} | ค่าความรักตอนนี้ {affection}/100 ({name}) | "
        f"ตอบเป็นกรอบบทพูด visual novel ตามฟอร์แมตใน output style โดยขึ้นต้นบรรทัดสีหน้าด้วย {face} แล้วตอบสั้นๆ 1-3 ประโยคในคาแรกเตอร์ตามระดับความสนิท (ซึนเดเระ: ปากแข็งแต่เขิน, เย็นชา: ปัดมือ/ไม่พอใจ, "
        "โดนเขย่า: โกรธ) เล่าท่าทางเป็น *ตัวเอียง* ไม่ต้องรายงานตัวเลข และห้ามเริ่มงานหรือเรียก tool ใดๆ"
    )
    log(f"NOTIFY {pending} -> {affection}")


def run():
    from pyjoycon import JoyCon, get_R_id

    ids = get_R_id()
    if not ids or ids[0] is None:
        raise RuntimeError("ไม่เจอ Joy-Con (R) ต่อ Bluetooth ก่อน")
    jc = JoyCon(*ids)
    log(f"connected {ids[2]}")
    det = pet_detect.Detector()
    last, peak, tick = None, 0.0, time.time()
    pending, last_event, last_notify = {"pet": 0, "shake": 0}, 0.0, 0.0
    while True:
        a = jc.get_status()["accel"]
        row = (a["x"], a["y"], a["z"])
        now = time.time()
        if row != last:  # report ใหม่เท่านั้น (~60Hz)
            last = row
            g = [v / RAW_PER_G for v in row]
            result = det.feed(now, *g)
            peak = max(peak, max(abs(v - w) for v, w in zip(g, det.grav)))
            if result:
                kind, value = result
                pending[kind] += 1
                last_event = now
                log(f"EVENT {kind} {value}")
        if now - tick >= 0.5:
            if _debug or peak > 0.08:  # ลงล็อกเฉพาะตอนมีการขยับ ไว้ปรับเกณฑ์
                log(f"motion peak={peak:.2f}g")
            peak, tick = 0.0, now
        if (pending["pet"] or pending["shake"]) and now - last_event >= QUIET_SEC \
                and now - last_notify >= MIN_NOTIFY_GAP:
            flush(pending)
            pending, last_notify = {"pet": 0, "shake": 0}, now
        time.sleep(0.004)


def main():
    global _debug
    ap = argparse.ArgumentParser()
    ap.add_argument("--debug", action="store_true")
    _debug = ap.parse_args().debug
    os.makedirs(lib.STATE_DIR, exist_ok=True)
    if already_running():
        return  # มี daemon อยู่แล้ว (กันสองตัวแย่ง Joy-Con)
    try:
        if os.path.getsize(LOG_FILE) > MAX_LOG_BYTES:
            os.remove(LOG_FILE)
    except OSError:
        pass
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))
    while True:  # หลุดแล้วต่อใหม่เอง (Joy-Con หลับ/ปิดฝา)
        try:
            run()
        except KeyboardInterrupt:
            break
        except Exception as e:  # noqa: BLE001
            log(f"error: {e} (ลองใหม่ใน 5 วิ)")
            time.sleep(5)


if __name__ == "__main__":
    main()
