"""State + tier logic shared by all hooks and the game script."""
import contextlib
import fcntl
import json
import os
import tempfile
import time

STATE_DIR = os.path.expanduser(os.environ.get("CLAUDE_CHAN_HOME", "~/.claude-chan"))
STATE_FILE = os.path.join(STATE_DIR, "state.json")
GAME_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "game.py")

START_AFFECTION = 10
DECAY_PER_DAY = 2
DECAY_MAX = 20

# (max affection, key, display name)
TIERS = [
    (20, "cold", "เย็นชา"),
    (50, "tsun", "ซึนเดเระ"),
    (80, "close", "สนิท"),
    (100, "love", "หัวใจเต็ม"),
]


def _defaults():
    now = time.time()
    return {
        "affection": START_AFFECTION,
        "last_seen": now,
        "last_gain": 0,
        "last_gift": 0,
        "last_trip": 0,
        "pet_cursor": 0,
        "pet_hour": {"start": 0, "gain": 0},
    }


@contextlib.contextmanager
def locked():
    """hook กับ daemon เขียน state พร้อมกันได้ ต้องล็อกก่อน load..save"""
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(os.path.join(STATE_DIR, "state.lock"), "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        yield


def load():
    state = _defaults()
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            state.update(json.load(f))
    except (OSError, ValueError):
        pass
    return state


def save(state):
    os.makedirs(STATE_DIR, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=STATE_DIR)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_FILE)


def clamp(n):
    return max(0, min(100, int(n)))


def add(state, delta):
    state["affection"] = clamp(state["affection"] + delta)
    return state["affection"]


def tier(affection):
    for limit, key, name in TIERS:
        if affection <= limit:
            return key, name
    return TIERS[-1][1], TIERS[-1][2]


def hearts(affection):
    n = round(affection / 20)
    return "♥" * n + "♡" * (5 - n)


def apply_decay(state):
    """ไม่ได้เจอกันนาน แต้มลดลง"""
    days = int((time.time() - state["last_seen"]) / 86400)
    if days > 0:
        add(state, -min(DECAY_MAX, days * DECAY_PER_DAY))
    state["last_seen"] = time.time()
    return days
