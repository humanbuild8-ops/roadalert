import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from crash_rules import CrashDetector

FPS = 30


def run(track_fn, seconds=8):
    det, events = CrashDetector(fps=FPS), []
    for f in range(seconds * FPS):
        events += det.update(f, track_fn(f))
    return events


def test_collision_is_detected():
    def tr(f):
        t = f / FPS
        ax = 100 + 300 * min(t, 1.1)          # A drives into B, then stops on contact
        return {1: (ax, 200, ax + 120, 260), 2: (500, 205, 620, 265)}
    ev = run(tr)
    assert len(ev) == 1, ev
    assert ev[0].confidence >= 0.6 and ev[0].speed_drop >= 0.6


def test_passing_in_other_lane_is_ignored():
    def tr(f):
        t = f / FPS
        return {1: (100 + 300 * t, 200, 220 + 300 * t, 260), 2: (500, 400, 620, 460)}
    assert run(tr) == []


def test_overlap_at_constant_speed_is_ignored():
    # B changes lane into A's box while both keep cruising: overlap, but no sudden slowdown
    def tr(f):
        t = f / FPS
        x = 100 + 200 * t
        by = 400 - 195 * min(1.0, max(0.0, t - 1.0))
        return {1: (x, 200, x + 120, 260), 2: (x + 60, by, x + 180, by + 60)}
    assert run(tr, 5) == []


def test_slow_traffic_jam_is_ignored():
    def tr(f):
        t = f / FPS
        x = 100 + 5 * t                        # crawling traffic, boxes touching
        return {1: (x, 200, x + 120, 260), 2: (x + 60, 205, x + 180, 265)}
    assert run(tr, 6) == []


def test_cooldown_prevents_duplicate_alerts():
    def tr(f):
        t = f / FPS
        ax = 100 + 300 * min(t, 1.1)
        return {1: (ax, 200, ax + 120, 260), 2: (500, 205, 620, 265)}
    assert len(run(tr, 12)) == 1


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("PASS", name)
