"""Crash-detection rule engine (no YOLO / OpenCV needed, so it is unit-testable).

Idea (same signal used by Ijjina et al. and Chand et al., see the base paper):
a collision is two tracked vehicles whose boxes overlap AND at least one of
them was moving beforehand and has abruptly slowed or stopped afterwards.

Speed is measured in "box heights per second" so it is roughly independent of
how far away the vehicle is. Scale change of the box is included, so a vehicle
that stops while the camera approaches it also registers as a speed drop.
"""
from collections import deque
from dataclasses import dataclass
import math


def iou(a, b):
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    if inter <= 0:
        return 0.0
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return inter / (area_a + area_b - inter + 1e-9)


@dataclass
class CrashEvent:
    frame: int
    time_s: float
    track_ids: tuple
    confidence: float
    iou: float
    speed_drop: float


class CrashDetector:
    def __init__(self, fps=30.0, iou_thr=0.10, settle_s=0.6, prior_window_s=2.0,
                 min_prior_speed=1.0, drop_ratio=0.6, min_conf=0.6,
                 cooldown_s=15.0, min_track_age_s=1.0, grace_frames=3):
        self.fps = fps
        self.iou_thr = iou_thr
        self.settle = int(settle_s * fps)
        self.prior_window = int(prior_window_s * fps)
        self.min_prior_speed = min_prior_speed
        self.drop_ratio = drop_ratio
        self.min_conf = min_conf
        self.cooldown = cooldown_s
        self.min_age = int(min_track_age_s * fps)
        self.grace = grace_frames
        self.hist = {}      # track_id -> deque[(frame, cx, cy, h)]
        self.pairs = {}     # (id_a, id_b) -> dict(start, last, max_iou, done)
        self.last_event_t = -1e9

    # ---------- helpers ----------
    def _speed(self, tid, f0, f1):
        pts = [p for p in self.hist.get(tid, ()) if f0 <= p[0] <= f1]
        if len(pts) < 3:
            return None
        total = 0.0
        for p, q in zip(pts, pts[1:]):
            h = max((p[3] + q[3]) / 2.0, 1.0)
            total += math.hypot(q[1] - p[1], q[2] - p[2]) / h
            total += abs(math.log(max(q[3], 1.0) / max(p[3], 1.0)))
        dur = (pts[-1][0] - pts[0][0]) / self.fps
        return total / dur if dur > 0 else None

    def _drop(self, tid, start, now):
        h = self.hist.get(tid)
        if not h or (h[-1][0] - h[0][0]) < self.min_age:
            return None
        prior = self._speed(tid, start - self.prior_window, start - int(0.1 * self.fps))
        post = self._speed(tid, start + int(0.1 * self.fps), now)
        if prior is None or post is None or prior < self.min_prior_speed:
            return None
        return max(0.0, min(1.0, 1.0 - post / prior))

    # ---------- main entry ----------
    def update(self, frame, boxes):
        """boxes: dict track_id -> (x1, y1, x2, y2). Returns list[CrashEvent]."""
        for tid, b in boxes.items():
            d = self.hist.setdefault(tid, deque(maxlen=int(self.fps * 6)))
            d.append((frame, (b[0] + b[2]) / 2, (b[1] + b[3]) / 2, max(b[3] - b[1], 1.0)))
        for tid in [t for t, d in self.hist.items() if frame - d[-1][0] > 2 * self.fps]:
            del self.hist[tid]

        ids = sorted(boxes)
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                ov = iou(boxes[a], boxes[b])
                if ov >= self.iou_thr:
                    p = self.pairs.setdefault((a, b), dict(start=frame, last=frame, max_iou=ov, done=False))
                    p['last'] = frame
                    p['max_iou'] = max(p['max_iou'], ov)
        for k in [k for k, p in self.pairs.items() if frame - p['last'] > self.grace]:
            del self.pairs[k]

        events = []
        now_t = frame / self.fps
        for (a, b), p in self.pairs.items():
            if p['done'] or frame - p['start'] < self.settle:
                continue
            p['done'] = True
            drops = [d for d in (self._drop(a, p['start'], frame), self._drop(b, p['start'], frame)) if d is not None]
            if not drops:
                continue
            drop = max(drops)
            if drop < self.drop_ratio:
                continue
            conf = min(0.95, 0.45 + 0.25 * min(1.0, p['max_iou'] / 0.3) + 0.30 * drop)
            if conf >= self.min_conf and now_t - self.last_event_t >= self.cooldown:
                self.last_event_t = now_t
                events.append(CrashEvent(frame, now_t, (a, b), round(conf, 2), round(p['max_iou'], 2), round(drop, 2)))
        return events
