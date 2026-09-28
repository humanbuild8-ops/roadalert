from typing import List, Optional

from fastapi import APIRouter, HTTPException

from ..models import Incident, IncidentCreate, IncidentStatus, NearbyDriver, VerificationCreate
from ..store import ALERT_RADIUS_KM, store
from ..ws_manager import manager

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.post("", response_model=Incident, status_code=201)
async def report_incident(payload: IncidentCreate):
    """A vehicle's on-device model reports a possible incident.

    This is the only data a car ever sends: no video, just location,
    heading and a confidence score.
    """
    incident = store.create(payload)
    await manager.broadcast({"event": "incident.reported", "incident": incident.model_dump(mode="json")})
    return incident


@router.get("", response_model=List[Incident])
async def list_incidents(status: Optional[IncidentStatus] = None):
    return store.list(status)


@router.get("/{incident_id}", response_model=Incident)
async def get_incident(incident_id: str):
    incident = store.get(incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    return incident


@router.post("/{incident_id}/verify", response_model=Incident)
async def verify_incident(incident_id: str, payload: VerificationCreate):
    """A second vehicle (or an authority) confirms the same incident.

    Once enough independent reports agree, the incident flips to
    'confirmed' and nearby drivers are alerted in the same call.
    """
    incident = store.add_verification(incident_id, payload.confidence)
    if not incident:
        raise HTTPException(404, "Incident not found")

    if incident.status == IncidentStatus.confirmed:
        await manager.broadcast({
            "event": "incident.confirmed",
            "incident": incident.model_dump(mode="json"),
            "alerted_driver_count": incident.alerted_driver_count,
        })
    return incident


@router.post("/{incident_id}/clear", response_model=Incident)
async def clear_incident(incident_id: str):
    incident = store.clear(incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    await manager.broadcast({"event": "incident.cleared", "incident": incident.model_dump(mode="json")})
    return incident


@router.get("/{incident_id}/nearby-drivers", response_model=List[NearbyDriver])
async def nearby_drivers(incident_id: str, radius_km: float = ALERT_RADIUS_KM):
    incident = store.get(incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    return store.nearby_drivers(incident.lat, incident.lng, radius_km)
