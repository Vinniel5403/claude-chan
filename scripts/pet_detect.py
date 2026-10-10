"""ตรวจท่า "ลูบหัว" จาก accelerometer ของ Joy-Con (ไม่ต้องมีฮาร์ดแวร์ก็เทสต์ได้)

ลูบ = ขยับไปมาเป็นจังหวะ แรงปานกลาง ; เขย่า = แรงเกิน
ค่า accel เป็นหน่วย g (raw / 4096)
"""
from collections import deque

WIN_SEC = 1.2        # หน้าต่างที่ดูการกลับทิศ
MIN_SAMPLES = 30
HYST = 0.25          # g: ต้องเกินเท่านี้ถึงนับว่าขยับจริง (กัน noise)
MIN_REVERSALS = 5
MAX_REVERSALS = 14   # เกินนี้ = สั่นถี่ ไม่ใช่ลูบ
PET_MIN_PEAK = 0.45  # g: ต้องขยับแรงถึงเท่านี้อย่างน้อยหนึ่งจังหวะ ไม่งั้นนับเป็นแค่ขยับเฉยๆ
SHAKE_PEAK = 2.0     # g: แรงเกินนี้ = เขย่า (ลูบช้าๆ < ~1.5g ; log จริงตอนเขย่าได้ 3-7g)
GRAVITY_ALPHA = 0.04  # low-pass ประมาณแรงโน้มถ่วง แล้วลบออก เหลือแรงจากการขยับ
EMIT_COOLDOWN = 1.5


class Detector:
    def __init__(self):
        self.grav = None
        self.buf = deque()
        self.last_emit = 0.0

    def feed(self, t, ax, ay, az):
        """ป้อนตัวอย่างทีละตัว คืน ("pet"|"shake", intensity) หรือ None"""
        cur = (ax, ay, az)
        if self.grav is None:
            self.grav = list(cur)
        self.grav = [g + (v - g) * GRAVITY_ALPHA for g, v in zip(self.grav, cur)]
        dyn = tuple(v - g for v, g in zip(cur, self.grav))
        self.buf.append((t, dyn))
        while self.buf and t - self.buf[0][0] > WIN_SEC:
            self.buf.popleft()
        if len(self.buf) < MIN_SAMPLES or t - self.last_emit < EMIT_COOLDOWN:
            return None
        result = self._classify()
        if result:
            self.last_emit = t
            self.buf.clear()
        return result

    def _classify(self):
        best_rev, peak = 0, 0.0
        for axis in range(3):
            rev, last_sign = 0, 0
            for _, d in self.buf:
                v = d[axis]
                peak = max(peak, abs(v))
                if abs(v) < HYST:
                    continue
                sign = 1 if v > 0 else -1
                if last_sign and sign != last_sign:
                    rev += 1
                last_sign = sign
            best_rev = max(best_rev, rev)
        if best_rev < MIN_REVERSALS or best_rev > MAX_REVERSALS:
            return None
        if peak < PET_MIN_PEAK:
            return None
        if peak > SHAKE_PEAK:
            return "shake", round(peak, 2)
        return "pet", round(peak, 2)
