"""อ่าน Joy-Con (R) ผ่าน Bluetooth ; ตรวจลูบ/เขย่า ; ใส่แต้มทันที ; แจ้ง Claude ผ่าน stdout

รันโดย monitor ของ plugin (monitors/monitors.json) : ทุกบรรทัดที่ print ออก stdout
จะกลายเป็นการแจ้งเตือนที่ปลุก Claude ให้ตอบ ดังนั้น stdout ใช้เฉพาะ "เหตุการณ์จริง"
ส่วน log ทั่วไปไปที่ joycon.log เท่านั้น

ทดสอบด้วยมือ: .venv/bin/python scripts/joycon_daemon.py --debug
"""
import argparse
import json
import os
import random
import sys
import threading
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
    if os.path.exists(BEAT_FLAG):
        _flag(notified=True)  # จากนี้ Stop hook ตัดการสั่นได้
    face = FACES["shake" if pending["shake"] else "pet"]
    key, name = lib.tier(affection)
    notify(
        f"[Claude-chan: สัมผัสจาก Joy-Con] {text} | ค่าความรักตอนนี้ {affection}/100 ({name}) | "
        f"ตอบเป็นกรอบบทพูด visual novel ตามฟอร์แมตใน output style โดยขึ้นต้นบรรทัดสีหน้าด้วย {face} แล้วตอบสั้นๆ 1-3 ประโยคในคาแรกเตอร์ตามระดับความสนิท (ซึนเดเระ: ปากแข็งแต่เขิน, เย็นชา: ปัดมือ/ไม่พอใจ, "
        "โดนเขย่า: โกรธ) เล่าท่าทางเป็น *ตัวเอียง* ไม่ต้องรายงานตัวเลข และห้ามเริ่มงานหรือเรียก tool ใดๆ"
    )
    log(f"NOTIFY {pending} -> {affection}")


# --- haptic: จังหวะหัวใจ (ตุบ-ตุบ) ตอนโดนลูบ ---
# rumble data 8 ไบต์ = [HF 4B][LF 4B] ; กลาง = 00 01 40 40 ; ใช้ลำโพงความถี่ต่ำ (160Hz) ไบต์ท้ายสุด 0x40(เงียบ)..0x72(แรงสุด)
_rumble_lock = threading.Lock()
_rumble_pn = 0
BEAT_FLAG = os.path.join(lib.STATE_DIR, "beating.json")  # มีไฟล์นี้ = ยังสั่นต่อ ; hook Stop เป็นคนลบ
BEAT_MAX_SEC = 90    # กันค้าง ถ้า Claude ไม่ตอบ/ไม่เจอ Stop
# ตุบ(แรง) - ตุบ(เบา) แล้วพัก = 1 ครั้งหัวใจ (~72 bpm)
LUB, DUB, REST = (0x5A, 0.10), (0x4C, 0.09), 0.34
ICE_SEC = 1.6       # เสียงน้ำแข็งนานเท่านี้
RAMP_SEC = 8       # เริ่มสั่นเบาแล้วไล่แรงขึ้นจนสุดใน N วินาที
RAMP_FROM = 0.3    # แรงเริ่มต้น (สัดส่วนของแรงเต็ม)
_beat_thread = None


def _rumble(jc, level):
    global _rumble_pn
    data = bytes([0x00, 0x01, 0x40, level]) * 2
    with _rumble_lock:
        _rumble_pn = (_rumble_pn + 1) & 0xF
        jc._joycon_device.write(b"\x10" + bytes([_rumble_pn]) + data)


def _flag(**kw):
    cur = {}
    try:
        with open(BEAT_FLAG) as f:
            cur = json.load(f)
    except (OSError, ValueError):
        pass
    cur.update(kw)
    with open(BEAT_FLAG, "w") as f:
        json.dump(cur, f)


def _beating():
    try:
        with open(BEAT_FLAG) as f:
            return time.time() - json.load(f).get("start", 0) < BEAT_MAX_SEC
    except (OSError, ValueError):
        return False


def heartbeat(jc):
    """เริ่มสั่นเป็นจังหวะหัวใจต่อเนื่องจนกว่า Claude จะตอบเสร็จ (hook Stop ลบ BEAT_FLAG)"""
    global _beat_thread
    if _beating() and _beat_thread and _beat_thread.is_alive():
        return
    _flag(start=time.time(), notified=False)

    def work():
        try:
            t0 = time.time()
            while _beating():
                k = RAMP_FROM + (1 - RAMP_FROM) * min(1.0, (time.time() - t0) / RAMP_SEC)
                for level, dur in (LUB, DUB):
                    level = 0x40 + int((level - 0x40) * k)  # 0x40 = เงียบ
                    _rumble(jc, level)
                    time.sleep(dur)
                    _rumble(jc, 0x40)
                    time.sleep(0.07)
                time.sleep(REST)
        except Exception as e:  # noqa: BLE001  (จอยหลุดกลางทาง ฯลฯ)
            log(f"rumble error: {e}")
        finally:
            try:
                _rumble(jc, 0x40)
            except Exception:  # noqa: BLE001
                pass
            try:
                os.remove(BEAT_FLAG)
            except OSError:
                pass
    _beat_thread = threading.Thread(target=work, daemon=True)
    _beat_thread.start()


def urgent(jc):
    """เขย่าแรง : เสียงก๊อกแก๊กเหมือนน้ำแข็งกระทบแก้ว ; จังหวะสุ่ม แรงสุ่ม ค่อยๆ เบาลงแล้วเงียบ"""
    def work():
        try:
            t0 = time.time()
            while True:
                k = 1 - (time.time() - t0) / ICE_SEC
                if k <= 0:
                    break
                _rumble(jc, 0x40 + int(random.uniform(0.35, 1.0) * 0x32 * (0.4 + 0.6 * k)))
                time.sleep(random.uniform(0.012, 0.03))      # กระทบสั้นๆ
                _rumble(jc, 0x40)
                time.sleep(random.uniform(0.03, 0.14))       # ช่วงเว้นไม่สม่ำเสมอ
        except Exception as e:  # noqa: BLE001
            log(f"rumble error: {e}")
        finally:
            try:
                _rumble(jc, 0x40)
            except Exception:  # noqa: BLE001
                pass
    threading.Thread(target=work, daemon=True).start()


STALL_SEC = 3  # ไม่มี report ใหม่นานเท่านี้ = จอยหลุด/หลับ (ปกติมาถี่ ~60Hz แม้วางนิ่ง)


def run():
    from pyjoycon import JoyCon, get_R_id

    ids = get_R_id()
    if not ids or ids[0] is None:
        raise RuntimeError("ไม่เจอ Joy-Con (R) ต่อ Bluetooth ก่อน (กดปุ่มบนจอยเพื่อปลุก)")
    jc = JoyCon(*ids)
    log(f"connected {ids[2]}")
    try:  # เปิดมอเตอร์สั่น (subcommand 0x48)
        jc._write_output_report(b"\x01", b"\x48", b"\x01")
    except Exception as e:  # noqa: BLE001
        log(f"enable vibration failed: {e}")
    started = time.time()
    try:
        _loop(jc)
    finally:
        log(f"disconnected after {int(time.time() - started)}s")
        try:
            jc._close()  # ปล่อย handle เก่า ไม่งั้นต่อใหม่ไม่ได้
        except Exception:  # noqa: BLE001
            pass


def _loop(jc):
    det = pet_detect.Detector()
    last, peak = None, 0.0
    tick = last_change = time.time()
    pending, last_event, last_notify = {"pet": 0, "shake": 0}, 0.0, 0.0
    while True:
        a = jc.get_status()["accel"]
        row = (a["x"], a["y"], a["z"])
        now = time.time()
        if row != last:  # report ใหม่เท่านั้น (~60Hz)
            last = row
            last_change = now
            g = [v / RAW_PER_G for v in row]
            result = det.feed(now, *g)
            peak = max(peak, max(abs(v - w) for v, w in zip(g, det.grav)))
            if result:
                kind, value = result
                pending[kind] += 1
                last_event = now
                log(f"EVENT {kind} {value}")
                if kind == "pet":
                    heartbeat(jc)
                else:
                    urgent(jc)
        elif now - last_change > STALL_SEC:
            raise RuntimeError("Joy-Con หลุด/หลับ (กดปุ่มบนจอยเพื่อปลุก)")
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
    last_err = None
    while True:  # หลุดแล้วต่อใหม่เอง (Joy-Con หลับ/ปิดฝา)
        try:
            run()
        except KeyboardInterrupt:
            break
        except Exception as e:  # noqa: BLE001
            if str(e) != last_err:  # ลงล็อกเฉพาะตอนสถานะเปลี่ยน ไม่รัวทุก 5 วิ
                log(f"error: {e} (จะลองใหม่ทุก 5 วิ)")
                last_err = str(e)
            time.sleep(5)


if __name__ == "__main__":
    main()
