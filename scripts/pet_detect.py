"""ตรวจท่า "ลูบหัว" จาก accelerometer ของ Joy-Con (ไม่ต้องมีฮาร์ดแวร์ก็เทสต์ได้)

ลูบ = แกว่งไปมาช้าๆ นุ่มๆ (~1-1.5Hz, 0.3-0.6g) ต่อเนื่องเกินครึ่งวิ
หยิบ/วางจอย = สั่นยิบทุก sample + กระแทกทีเดียว (ต้องไม่นับเป็นลูบ)
เขย่า = แรงเกิน 1g กลับไปกลับมาหลายรอบ
ค่า accel เป็นหน่วย g (raw / 4096) ; เกณฑ์ปรับจาก log จริง (อัดด้วยมือ ติดป้าย วาง/ลูบ)
"""
from collections import deque

WIN_SEC = 2.0        # หน้าต่างที่ดูการกลับทิศ (ลูบจริงกลับทิศทุก 0.3-0.5 วิ)
MIN_SAMPLES = 30
GRAVITY_ALPHA = 0.04  # low-pass ประมาณแรงโน้มถ่วง แล้วลบออก เหลือแรงจากการขยับ
SMOOTH_ALPHA = 0.25  # EMA ตัดสั่นยิบจากการหยิบ/กระแทก ให้เหลือแต่การแกว่งช้าๆ
EMIT_COOLDOWN = 1.5

# ลูบ: นับบนสัญญาณที่ smooth แล้ว
HYST = 0.15          # g: ต้องเกินเท่านี้ถึงนับว่าขยับจริง (กัน noise)
MIN_GAP = 0.15       # วิ: กลับทิศถี่กว่านี้ = สั่นยิบ ไม่ใช่ลูบ
MAX_GAP = 0.8        # วิ: กลับทิศห่างกว่านี้ = มีช่วงหยุดนิ่งคั่น (วางแล้วหยิบใหม่) ไม่ใช่ลูบต่อเนื่อง
MIN_REVERSALS = 3
MIN_SPAN = 0.6       # วิ: กลับทิศครั้งแรกถึงครั้งสุดท้ายต้องห่างเท่านี้ (ลูบต่อเนื่อง ไม่ใช่กระตุกทีเดียว)
PET_MIN_PEAK = 0.3   # g: ต้องขยับแรงถึงเท่านี้อย่างน้อยหนึ่งจังหวะ (smooth แล้ว)
PET_MAX_RAW = 1.2    # g: มีกระแทกแรงกว่านี้ในหน้าต่าง = หยิบ/วางจอย (ลูบจริงดิบสุด ~1.3g แต่ส่วนใหญ่ < 1g)

# เขย่า: นับบนสัญญาณดิบ แรงๆ เท่านั้น
SHAKE_HYST = 1.0     # g: วางจอยกระแทกแรงได้ทีเดียว เขย่าจริงแกว่ง ±1g หลายรอบ
SHAKE_REVERSALS = 4
SHAKE_PEAK = 2.0     # g: log จริงตอนเขย่าได้ 3-7g


def _reversals(samples, axis, hyst, min_gap=0.0):
    """เวลาที่สัญญาณแกน axis กลับทิศ (ข้ามช่วง |v| < hyst ; กลับทิศถี่กว่า min_gap ไม่นับ)"""
    times, last_sign = [], 0
    for t, v in samples:
        v = v[axis]
        if abs(v) < hyst:
            continue
        sign = 1 if v > 0 else -1
        if last_sign and sign != last_sign and (not times or t - times[-1] >= min_gap):
            times.append(t)
        last_sign = sign
    return times


class Detector:
    def __init__(self):
        self.grav = None
        self.smooth = [0.0, 0.0, 0.0]
        self.buf = deque()   # (t, dyn, smooth)
        self.last_emit = 0.0
        self.info = ""       # ไว้ลง log ตอนปรับเกณฑ์

    def feed(self, t, ax, ay, az):
        """ป้อนตัวอย่างทีละตัว คืน ("pet"|"shake", intensity) หรือ None"""
        cur = (ax, ay, az)
        if self.grav is None:
            self.grav = list(cur)
        self.grav = [g + (v - g) * GRAVITY_ALPHA for g, v in zip(self.grav, cur)]
        dyn = tuple(v - g for v, g in zip(cur, self.grav))
        self.smooth = [s + (d - s) * SMOOTH_ALPHA for s, d in zip(self.smooth, dyn)]
        self.buf.append((t, dyn, tuple(self.smooth)))
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
        raw = [(t, d) for t, d, _ in self.buf]
        peak = max(abs(v) for _, d in raw for v in d)
        if peak > SHAKE_PEAK and max(len(_reversals(raw, a, SHAKE_HYST)) for a in range(3)) >= SHAKE_REVERSALS:
            self.info = f"peak={peak:.2f}"
            return "shake", round(peak, 2)

        if peak > PET_MAX_RAW:
            return None
        smooth = [(t, s) for t, _, s in self.buf]
        for axis in range(3):
            rev = _reversals(smooth, axis, HYST, MIN_GAP)
            span = rev[-1] - rev[0] if rev else 0.0
            if len(rev) < MIN_REVERSALS or span < MIN_SPAN:
                continue
            if max(b - a for a, b in zip(rev, rev[1:])) > MAX_GAP:
                continue
            spk = max(abs(s[axis]) for _, s in smooth)
            if spk < PET_MIN_PEAK:
                continue
            self.info = f"axis={'xyz'[axis]} rev={len(rev)} span={span:.2f}s peak={spk:.2f}"
            return "pet", round(spk, 2)
        return None
