"""ออกจาก Claude Code : ปิดเพลงและเสียงพากย์ที่ยังเล่นค้าง"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tts  # noqa: E402

tts.stop_bgm()
tts.stop()
sys.exit(0)
