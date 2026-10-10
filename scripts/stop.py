"""Claude ตอบจบแล้ว : หยุดการสั่นหัวใจของ Joy-Con (ถ้าเป็นการตอบการลูบ)"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

BEAT_FLAG = os.path.join(lib.STATE_DIR, "beating.json")

try:
    with open(BEAT_FLAG) as f:
        flag = json.load(f)
    if flag.get("notified"):  # หยุดเฉพาะหลังแจ้ง Claude แล้ว (กัน turn เก่าที่เพิ่งจบมาตัดทิ้ง)
        os.remove(BEAT_FLAG)
except (OSError, ValueError):
    pass
sys.exit(0)
