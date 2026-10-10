import json
import sys

import greet
import lib
import persona
import sprites
import tts

try:
    data = json.load(sys.stdin)
except ValueError:
    data = {}
opening = data.get("source", "startup") in ("startup", "resume")  # ไม่ใช่ /clear หรือ /compact

with lib.locked():
    state = lib.load()
    days = lib.apply_decay(state)
    lib.save(state)

message = sprites.render(state, days=days)
context = persona.build(state, days_away=days)
if opening:
    tts.play_bgm()
    hello = greet.box(greet.line(state, days))
    message += "\n\n" + hello
    tts.speak(hello)
    context += f"\nตอนเปิดเกม คุณทักผู้ใช้ไปแล้วว่า: {hello.splitlines()[2]} (ไม่ต้องทักซ้ำ เล่นต่อจากนั้น)"

print(json.dumps({
    "systemMessage": message,
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": context,
    }
}, ensure_ascii=False))
sys.exit(0)
