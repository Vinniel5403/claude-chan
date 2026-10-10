---
name: joycon-setup
description: ติดตั้งระบบ Joy-Con ให้ Claude-chan (ผู้ใช้สั่งเท่านั้น)
disable-model-invocation: true
---

รัน `bash "${CLAUDE_PLUGIN_ROOT}/scripts/setup_joycon.sh"` ด้วย Bash tool

- ถ้าขึ้น `OK:` บอกผู้ใช้ว่าติดตั้งเสร็จ ให้ต่อ Joy-Con (R) ผ่าน Bluetooth แล้วเปิด Claude Code ใหม่ (daemon เริ่มตอนเปิด session)
- ถ้า error ให้สรุปสาเหตุสั้นๆ และบอกวิธีแก้ (เช่น ไม่มี python3 → ติดตั้ง python3 หรือ uv)
