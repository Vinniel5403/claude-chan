# Claude-chan

เกมจีบ Claude-chan ใน Claude Code — ค่าความสัมพันธ์ต่ำ = เรื่องมาก/ไม่ยอมทำงาน, ค่าสูง = เชื่อฟัง

## ติดตั้ง

ใน Claude Code:

```
/plugin marketplace add Vinniel5403/claude-chan
/plugin install claude-chan@claude-chan
```

แล้ว restart Claude Code

- ต้องมี `python3` (ใช้แค่ stdlib)
- เปิดสไตล์ visual novel: `/output-style` → เลือก **Visual Novel**
- ดูค่าความรัก: `/claude-chan:status`
- เซฟเกมเก็บที่ `~/.claude-chan/` (เปลี่ยนได้ด้วย env `CLAUDE_CHAN_HOME`)

## สายชาร์จ

โน้ตบุ๊ก (macOS/Linux) เสียบๆ ถอดๆ สายชาร์จถี่ๆ (ถอด-เสียบ 2 ครั้งใน 10 วิ) แล้ว Claude-chan จะเขิน ใช้ได้เลยไม่ต้องติดตั้งเพิ่ม

## Joy-Con (ไม่บังคับ)

ลูบ/เขย่า Joy-Con (R) เพื่อเอาใจ Claude-chan และกดปุ่ม **A / B** เลือกเมนู `[1]` / `[2]` ท้ายคำตอบได้เลยไม่ต้องพิมพ์ (จอยสั่น 1 ที = เลือกแล้ว, 2 ทีเบาๆ = ยังไม่มีเมนูให้เลือก)

ติดตั้ง พิมพ์ใน Claude Code:

```
/claude-chan:joycon-setup
```

ติดตั้งให้อัตโนมัติที่ `~/.claude-chan/venv` (อัปเดต plugin แล้วไม่หาย) จากนั้นต่อ Joy-Con ผ่าน Bluetooth แล้วเปิด Claude Code ใหม่

ไม่ติดตั้งก็เล่นได้ปกติ แค่ไม่มีฟีเจอร์ Joy-Con

## อัปเดต

```
/plugin marketplace update claude-chan
```
