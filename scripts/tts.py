"""เสียงของ Claude-chan : พากย์บทพูดใน 「 」 ด้วย Paxa TTS (https://paxalabs.com/th/docs) + เพลงตอนเปิด ; ใช้แค่ stdlib

Stop hook เรียก speak() ; ยิง API + เล่นเสียงใน process แยก ไม่หน่วง Claude
SessionStart เรียก play_bgm() ; เล่นพร้อมเสียงพากย์ได้ ; เพลงหยุดตอน SessionEnd
หรือตอน process ของ Claude Code หายไป (ปิด terminal ทิ้ง / crash) ผ่านตัวเฝ้า _bgm_watch
ตั้งค่าที่ ~/.claude-chan/tts.json :
    {"api_key": "pxa_...", "voice": "lukchup", "speed": 1.0, "enabled": true,
     "bgm": true, "bgm_volume": 0.4}
หรือใช้ env PAXA_API_KEY แทน api_key ; ไม่มี key = ไม่พากย์
เพลง: ~/.claude-chan/bgm.mp3 หรือไฟล์ .mp3 ในโฟลเดอร์ plugin (gitignore ไว้ ห้าม commit เพลงมีลิขสิทธิ์)

ทดสอบด้วยมือ: python3 scripts/tts.py "สวัสดีค่ะ"
"""
import glob
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

CONFIG_FILE = os.path.join(lib.STATE_DIR, "tts.json")
PID_FILE = os.path.join(lib.STATE_DIR, "tts.pid")
AUDIO_FILE = os.path.join(lib.STATE_DIR, "tts.mp3")
LOG_FILE = os.path.join(lib.STATE_DIR, "tts.log")
BGM_PID_FILE = os.path.join(lib.STATE_DIR, "bgm.pid")
PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_URL = os.environ.get("PAXA_API_URL", "https://api.paxalabs.com") + "/v1/tts"
MODEL = "paxa-tts-flash-v1"
DEFAULT_VOICE = "lukchup"  # เสียงการ์ตูน แหลม น่ารัก
MAX_CHARS = 400            # กันเปลืองเครดิต (10 เครดิต / 1,000 ตัวอักษร)
QUOTE = re.compile(r"「(.*?)」", re.S)
CODE = re.compile(r"```.*?```|`[^`\n]*`", re.S)  # 「」 ในโค้ดของ ▸ ผลงาน ไม่ใช่บทพูด
# เหลือแค่ตัวอักษร ตัวเลข และวรรคตอนที่อ่านออกเสียงได้ (ตัด emoji/♥/สัญลักษณ์)
JUNK = re.compile(r"[^\w\s฀-๿.,!?…~\-'\"()]")


def config():
    cfg = {}
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        pass
    cfg.setdefault("api_key", os.environ.get("PAXA_API_KEY", ""))
    return cfg


def extract(text):
    """บทพูดทุกช่วงใน 「 」 ต่อกัน -> str (ว่าง = ไม่มีอะไรให้พูด)"""
    parts = [JUNK.sub("", p).replace("~", "").strip() for p in QUOTE.findall(CODE.sub("", text or ""))]
    return " ".join(p for p in parts if p)[:MAX_CHARS]


def log(msg):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")
    except OSError:
        pass


def stop():
    """หยุดเสียงที่พูดค้างอยู่ (พูดใหม่ทับ ไม่ให้เสียงซ้อน)"""
    try:
        with open(PID_FILE) as f:
            os.killpg(int(f.read().strip()), signal.SIGTERM)
    except (OSError, ValueError):
        pass


def _bgm_file():
    files = [os.path.join(lib.STATE_DIR, "bgm.mp3")] + sorted(glob.glob(os.path.join(PLUGIN_ROOT, "*.mp3")))
    return next((f for f in files if os.path.isfile(f)), None)


def _claude_pid():
    """ไล่ขึ้นไปหา process ของ Claude Code ที่เรียก hook นี้ (hook อาจรันผ่าน shell อีกชั้น)"""
    pid = os.getppid()
    for _ in range(6):
        try:
            out = subprocess.run(["ps", "-o", "ppid=,command=", "-p", str(pid)],
                                 capture_output=True, text=True, timeout=5).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            break
        if not out:
            break
        ppid, cmd = out.split(None, 1)
        if "claude" in os.path.basename(cmd.split()[0]).lower():
            return pid
        pid = int(ppid)
    return os.getppid()


def play_bgm():
    """SessionStart: เปิดเพลงเบื้องหลังพร้อมตัวเฝ้า (ไม่รอ)"""
    cfg = config()
    path = _bgm_file()
    if not path or cfg.get("bgm") is False or not shutil.which("afplay"):
        return
    stop_bgm()
    p = subprocess.Popen(
        [sys.executable, os.path.abspath(__file__), "--bgm", str(_claude_pid()), str(cfg.get("bgm_volume", 0.4)), path],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,  # Claude Code ไม่รอ ; stop_bgm ฆ่าทั้งกลุ่ม (ตัวเฝ้า + afplay)
    )
    with open(BGM_PID_FILE, "w") as f:
        f.write(str(p.pid))


def _bgm_watch(owner, vol, path):
    """เล่นเพลงจนจบ หรือจน Claude Code (owner) ปิด"""
    player = subprocess.Popen(["afplay", "-v", vol, path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    while player.poll() is None:
        try:
            os.kill(owner, 0)
        except OSError:
            player.terminate()
            break
        time.sleep(1)


def stop_bgm():
    if lib._alive(BGM_PID_FILE, "tts.py --bgm"):  # เช็คชื่อด้วย กันไปฆ่า process อื่นที่ได้ pid ซ้ำ
        with open(BGM_PID_FILE) as f:
            os.killpg(int(f.read().strip()), signal.SIGTERM)


def speak(reply):
    """Stop hook: ส่งบทพูดของคำตอบไปพากย์ใน process แยก แล้วคืนทันที"""
    cfg = config()
    text = extract(reply)
    if not text or not cfg.get("api_key") or cfg.get("enabled") is False:
        return
    subprocess.Popen(
        [sys.executable, os.path.abspath(__file__), text],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,  # Claude Code ไม่รอ และ stop() ฆ่าทั้งกลุ่มได้
    )


def _player():
    for cmd in (["afplay"], ["mpg123", "-q"], ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]):
        if shutil.which(cmd[0]):
            return cmd
    return None


def _say(text):
    cfg = config()
    stop()
    os.makedirs(lib.STATE_DIR, exist_ok=True)
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpgrp()))
    body = {"text": text, "voice": cfg.get("voice", DEFAULT_VOICE), "model": MODEL, "format": "mp3"}
    if cfg.get("speed"):
        body["speed"] = cfg["speed"]
    req = urllib.request.Request(API_URL, data=json.dumps(body, ensure_ascii=False).encode(), headers={
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            audio = r.read()
            log(f"OK {len(text)} chars, {r.headers.get('x-credits-charged', '?')} credits")
    except urllib.error.HTTPError as e:
        log(f"HTTP {e.code} {e.read()[:300].decode('utf-8', 'replace')}")
        return
    except (urllib.error.URLError, OSError) as e:
        log(f"error: {e}")
        return
    with open(AUDIO_FILE, "wb") as f:
        f.write(audio)
    player = _player()
    if not player:
        log("ไม่เจอโปรแกรมเล่นเสียง (afplay / mpg123 / ffplay)")
        return
    subprocess.run(player + [AUDIO_FILE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    if sys.argv[1:2] == ["--bgm"] and len(sys.argv) == 5:
        _bgm_watch(int(sys.argv[2]), sys.argv[3], sys.argv[4])
        sys.exit(0)
    if len(sys.argv) != 2:
        print("usage: tts.py <ข้อความ>")
        sys.exit(1)
    try:
        _say(sys.argv[1])
    finally:
        try:
            with open(PID_FILE) as f:
                if int(f.read().strip()) == os.getpgrp():
                    os.remove(PID_FILE)
        except (OSError, ValueError):
            pass
