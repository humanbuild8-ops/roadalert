"""Backup demo with NO video and NO YOLO: feeds a scripted (synthetic) collision through the
real crash rule and posts it to the real backend. Use it to show the pipeline if the model
or a clip is not available. It is a simulation, not real detection: say so when presenting.

  python synthetic_demo.py --api http://localhost:8000
"""
import argparse

from api_client import BackendClient
from crash_rules import CrashDetector

FPS = 30


def scripted_tracks(f):
    t = f / FPS
    # car A drives right at 300 px/s, hits stationary car B and stops on contact
    ax = 100 + 300 * min(t, 1.1)
    return {1: (ax, 200, ax + 120, 260), 2: (500, 205, 620, 265)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8000")
    a = ap.parse_args()
    det, client = CrashDetector(fps=FPS), BackendClient(a.api)
    for f in range(0, 8 * FPS):
        for ev in det.update(f, scripted_tracks(f)):
            print(f"[CRASH] t={ev.time_s:.1f}s conf={ev.confidence} iou={ev.iou} drop={ev.speed_drop}")
            inc = client.report(ev.confidence)
            if inc:
                print("        reported ->", inc["id"], inc["status"])
                out = client.verify(inc["id"], max(0.6, ev.confidence - 0.05))
                if out:
                    print("        DEMO second vehicle ->", out["status"], "| drivers alerted:", out["alerted_driver_count"])


if __name__ == "__main__":
    main()
