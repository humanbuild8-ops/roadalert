# RoadAlert — Accident Detection & Smart Rerouting

A working demo of the project from the review deck: car cameras detect
accidents, the cloud verifies them, and drivers behind the incident get
warned and rerouted.

```
roadalert-website/
├── frontend/              live operations-console dashboard (static, no build step)
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
├── backend/                FastAPI service: report → verify → alert → clear
│   ├── app/
│   │   ├── main.py         app + CORS + router wiring
│   │   ├── models.py       Incident / verification / stats schemas
│   │   ├── store.py        in-memory store (swap-in point for MongoDB)
│   │   ├── ws_manager.py   WebSocket broadcast to connected dashboards
│   │   └── routers/        incidents.py · stats.py · ws.py
│   ├── requirements.txt
│   └── .env.example
└── README.md                you are here
```

## See it live in under a minute

The frontend needs nothing installed — it simulates its own traffic,
its own accident, and its own alert cycle, styled as a highway
operations console:

```bash
cd frontend
python3 -m http.server 5500
# open http://localhost:5500 in a browser
```

Click **"Report accident now"** to trigger the sequence on demand, or
just watch — it also runs the cycle automatically every ~16 seconds.
That is enough to demo the idea with no backend running at all.

## Wiring it to the real backend

Start the API:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# interactive API docs: http://localhost:8000/docs
```

With the backend running, reload the frontend: it opens
`ws://localhost:8000/ws/incidents`, the top-right badge switches from
*simulated feed* to *live backend feed*, and **"Report accident now"**
posts a real `IncidentCreate` event instead of animating a local one.

### The verification rule

An incident is only announced once **two independent reports** (the
original detection plus at least one more, from another vehicle or an
authority) both average at or above a confidence of `0.6`
(`CONFIRM_VERIFICATIONS_NEEDED` / `CONFIRM_MIN_CONFIDENCE` in
`app/store.py`). This is the same rule the "Project Gaps" slide
describes: no single camera can trigger an alert on its own.

### Try the API directly

```bash
# a car reports a possible collision
curl -X POST localhost:8000/api/incidents \
  -H "Content-Type: application/json" \
  -d '{"lat":12.9716,"lng":77.5946,"heading_deg":15,"confidence":0.7,"incident_type":"collision"}'

# a second vehicle confirms it — this call is the one that
# flips the incident to "confirmed" and alerts nearby drivers
curl -X POST localhost:8000/api/incidents/<id>/verify \
  -H "Content-Type: application/json" \
  -d '{"confidence":0.8,"source":"vehicle"}'
```

## What is real here, and what is a stand-in

This is a presentation-ready demo, not the production system, and it
is honest about the difference:

| Piece | In this repo | In production |
|---|---|---|
| Accident detection | not included | an on-device YOLO-based classifier running on the vehicle's phone or dashcam |
| Data store | in-memory Python dict (`app/store.py`) | MongoDB with a `2dsphere` geospatial index |
| Push alerts | WebSocket broadcast to whoever is connected | Firebase Cloud Messaging targeted at the drivers a routing query actually matches |
| Nearby drivers | a seeded random generator (`store.nearby_drivers`) | live GPS pings from the driver app, queried by radius and heading |
| Rerouting | a drawn arc on the demo map | a real routing engine (Google Maps / OSRM) call |
| Frontend build | none — plain HTML/CSS/JS | could move to Flutter (as in the review deck) for an installable driver app |

Swapping any one of these in only touches the matching file — the API
contract in `models.py` and the verify-then-alert flow in
`store.py` / `routers/incidents.py` are written to stay the same.

## Privacy, by design

Only an event packet ever leaves a vehicle: latitude, longitude,
heading, an optional speed, a confidence score, and an incident type
(see `IncidentCreate` in `app/models.py`). No video, image, or personal
identifier is part of that payload or stored anywhere in this project.


## Planner simulator (new)

`frontend/planner.html` is a standalone simulator comparing a baseline planner with the adaptive planner on an unstructured Indian-style road (six scenarios, live metrics, a 30-run comparison table and CSV export). Open it at http://localhost:5500/planner.html. If the backend is running, a confirmed incident adds a stalled vehicle ahead in both worlds.

## Folder layout

- `frontend/` console (`index.html`) and planner simulator (`planner.html`)
- `backend/` FastAPI incident API
- `detection/` YOLO crash detection (`detect.py`, `synthetic_demo.py`)
