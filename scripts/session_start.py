import json
import sys

import lib
import persona
import sprites

with lib.locked():
    state = lib.load()
    days = lib.apply_decay(state)
    lib.save(state)

print(json.dumps({
    "systemMessage": sprites.render(state),
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": persona.build(state, days_away=days),
    }
}, ensure_ascii=False))
sys.exit(0)
