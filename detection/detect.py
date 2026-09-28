"""RoadAlert on-device detection: dashcam video -> YOLOv8 tracking -> crash rule -> backend.

Examples
  python detect.py --source clips/crash.mp4 --show --simulate-second-vehicle
  python detect.py --source 0 --show                # webcam
  python detect.py --source clips/crash.mp4 --no-post --save out.mp4
"""
import argparse
import time

import cv2

from api_client import BackendClient
from crash_rules import CrashDetector

VEHICLE_CLASSES = [2, 3, 5, 7]  # COCO: car, motorcycle, bus, truck


def parse():
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, help="video file path, or 0 for webcam")
    p.add_argument("--model", default="yolov8n.pt", help="YOLOv8 weights (downloaded automatically)")
    p.add_argument("--api", default="http://localhost:8000")
    p.add_argument("--lat", type=float, default=12.9716)
    p.add_argument("--lng", type=float, default=77.5946)
    p.add_argument("--heading", type=float, default=15.0)
    p.add_argument("--show", action="store_true", help="show live window (press q to quit)")
    p.add_argument("--save", help="write annotated video to this path")
    p.add_argument("--no-post", action="store_true", help="dry run: do not call the backend")
    p.add_argument("--simulate-second-vehicle", action="store_true",
                   help="DEMO ONLY: send a second confirming report so the backend confirms the incident")
    p.add_argument("--conf", type=float, default=0.3, help="YOLO detection confidence")
    p.add_argument("--iou-thr", type=float, default=0.10)
    p.add_argument("--drop-ratio", type=float, default=0.6)
    p.add_argument("--min-prior-speed", type=float, default=1.0)
    p.add_argument("--cooldown", type=float, default=15.0)
    return p.parse_args()


def main():
    a = parse()
    from ultralytics import YOLO  # imported here so crash_rules/tests work without it
    model = YOLO(a.model)
    src = int(a.source) if a.source.isdigit() else a.source
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        raise SystemExit(f"Cannot open source: {a.source}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    det = CrashDetector(fps=fps, iou_thr=a.iou_thr, drop_ratio=a.drop_ratio,
                        min_prior_speed=a.min_prior_speed, cooldown_s=a.cooldown)
    client = None if a.no_post else BackendClient(a.api, a.lat, a.lng, a.heading)
    writer = None
    banner_until, frame_no, t0 = -1, 0, time.time()

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        res = model.track(frame, persist=True, tracker="bytetrack.yaml", classes=VEHICLE_CLASSES,
                          conf=a.conf, verbose=False)[0]
        boxes = {}
        if res.boxes is not None and res.boxes.id is not None:
            for tid, xyxy in zip(res.boxes.id.int().cpu().tolist(), res.boxes.xyxy.cpu().tolist()):
                boxes[tid] = tuple(xyxy)

        for ev in det.update(frame_no, boxes):
            print(f"[CRASH] t={ev.time_s:.1f}s tracks={ev.track_ids} conf={ev.confidence} "
                  f"iou={ev.iou} speed_drop={ev.speed_drop}")
            banner_until = frame_no + int(3 * fps)
            if client:
                inc = client.report(ev.confidence)
                if inc:
                    print(f"        reported -> incident {inc['id']} ({inc['status']})")
                    if a.simulate_second_vehicle:
                        print("        DEMO: simulating a second vehicle's confirmation")
                        out = client.verify(inc["id"], max(0.6, ev.confidence - 0.05))
                        if out:
                            print(f"        backend status: {out['status']}, drivers alerted: {out['alerted_driver_count']}")

        for tid, (x1, y1, x2, y2) in boxes.items():
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (242, 169, 59), 2)
            cv2.putText(frame, f"#{tid}", (int(x1), int(y1) - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (242, 169, 59), 1)
        if frame_no < banner_until:
            cv2.rectangle(frame, (0, 0), (frame.shape[1], 46), (46, 59, 226), -1)
            cv2.putText(frame, "ACCIDENT DETECTED - alert sent", (14, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)

        if a.save:
            if writer is None:
                h, w = frame.shape[:2]
                writer = cv2.VideoWriter(a.save, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
            writer.write(frame)
        if a.show:
            cv2.imshow("RoadAlert detection", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        frame_no += 1

    cap.release()
    if writer:
        writer.release()
    cv2.destroyAllWindows()
    print(f"Processed {frame_no} frames in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
