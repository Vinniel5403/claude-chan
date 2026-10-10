"""Claude ตอบจบแล้ว : หยุดการสั่นหัวใจของ Joy-Con (ถ้าเป็นการตอบการลูบ) และจำเมนูล่าสุดไว้ให้ปุ่ม A/B"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import menu  # noqa: E402

BEAT_FLAG = os.path.join(lib.STATE_DIR, "beating.json")

try:
    with open(BEAT_FLAG) as f:
        flag = json.load(f)
    if flag.get("notified"):  # หยุดเฉพาะหลังแจ้ง Claude แล้ว (กัน turn เก่าที่เพิ่งจบมาตัดทิ้ง)
        os.remove(BEAT_FLAG)
except (OSError, ValueError):
    pass

try:
    data = json.load(sys.stdin)
except ValueError:
    data = {}
last = data.get("last_assistant_message")
menu.store(menu.parse(last) if isinstance(last, str) else menu.last_menu(data.get("transcript_path")))
sys.exit(0)
