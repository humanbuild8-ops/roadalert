"""RoadAlert backend — cloud verification, alerting and the live feed.

Run with:  uvicorn app.main:app --reload --port 8000
Docs at:   http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import incidents, stats, ws

app = FastAPI(
    title="RoadAlert API",
    description="Accident detection, verification, alerting and rerouting backend.",
    version="0.1.0",
)

# Wide open for local development against the /frontend demo. Narrow this
# to the real driver-app and dashboard origins before deploying.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(incidents.router)
app.include_router(stats.router)
app.include_router(ws.router)


@app.get("/", tags=["health"])
async def root():
    return {"service": "roadalert-api", "status": "ok"}
