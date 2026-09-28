# RoadAlert detection module

Dashcam video -> YOLOv8 vehicle tracking -> crash rule -> backend (`../backend`) -> live console (`../frontend`).

Put this `detection/` folder in the project root, next to `frontend/` and `backend/`.

## Setup
```bash
cd detection
python -m venv venv
venv\Scripts\activate          # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
```
The first run downloads the small `yolov8n.pt` weights automatically (needs internet once).

## Run order
1. Terminal 1: start the backend (`cd backend`, `uvicorn app.main:app --reload --port 8000`).
2. Open the frontend in the browser (badge should say "live backend feed").
3. Terminal 2, real video:
```bash
python detect.py --source clips/crash.mp4 --show --simulate-second-vehicle
```
Use `--source 0` for a webcam, `--no-post` for a dry run, `--save out.mp4` to save the annotated video.

`--simulate-second-vehicle` is **demo only**: with one camera there is no second vehicle, so it sends a
second confirming report to trigger the backend's two-source rule. Say this out loud in the review.

## No clip or model available? (backup demo)
```bash
python synthetic_demo.py
```
Feeds a scripted collision through the same rule engine and backend. It is a simulation, not real detection.

## Where to get test clips
Public dashcam accident datasets: DoTA and DAD (see references in the research paper), or your own recordings.
Check each dataset's licence, and use clips for the college project only.

## How the rule works (`crash_rules.py`)
A crash is flagged when two tracked vehicles' boxes overlap (IoU >= 0.10) and, after the overlap has settled
for 0.6 s, at least one vehicle's speed has dropped by >= 60% compared with the 2 s before contact.
Speed is measured in box-heights per second (includes box scale change). Confidence combines overlap and speed drop.

| Flag | Default | Effect |
|---|---|---|
| `--iou-thr` | 0.10 | how much boxes must overlap |
| `--drop-ratio` | 0.6 | how sharp the slowdown must be |
| `--min-prior-speed` | 1.0 | vehicles slower than this before contact are ignored (traffic jams) |
| `--cooldown` | 15 | seconds before another alert can fire |

## Tests
```bash
python tests/test_crash_rules.py
```
Covers: real collision detected, other-lane pass ignored, lane-change overlap ignored, traffic jam ignored, no duplicate alerts.

## Honest limitations (mention these to the panel)
- The thresholds are hand-set and **untuned**. Test on real clips and adjust the flags above.
- Centroid/speed rules struggle with heavy occlusion, night/rain, and a fast-moving camera. Expect some false alarms.
- Nothing here has been measured on a dataset yet, so the 90% / 3 s / 5% figures in the paper are still targets.
- Later improvement: train or fine-tune a classifier on DoTA/DAD frames and use this rule as a fallback.
