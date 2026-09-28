"""In-memory incident store.

This stands in for the MongoDB-backed store described in the project's
architecture (a `2dsphere` index on incident location, verification
documents keyed by incident id). It keeps the same shape and the same
verification/confirmation rule so the API contract will not change when
a real database is wired in — see ``README.md`` for that migration note.
"""
import math
import random
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .models import Incident, IncidentCreate, IncidentStatus, NearbyDriver, Stats

CONFIRM_VERIFICATIONS_NEEDED = 2
CONFIRM_MIN_CONFIDENCE = 0.6
ALERT_RADIUS_KM = 5.0


def haversine_km(lat1, lng1, lat2, lng2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


class IncidentStore:
    def __init__(self) -> None:
        self._incidents: Dict[str, Incident] = {}
        self._verifications: Dict[str, List[float]] = {}
        self.alerts_sent_today = 0
        self._latencies_ms: List[float] = []

    # ---- incidents ----
    def create(self, payload: IncidentCreate) -> Incident:
        incident = Incident(
            id=str(uuid.uuid4())[:8],
            lat=payload.lat,
            lng=payload.lng,
            heading_deg=payload.heading_deg,
            incident_type=payload.incident_type,
            status=IncidentStatus.pending,
            confidence=payload.confidence,
            verification_count=0,
            reported_at=datetime.now(timezone.utc),
        )
        self._incidents[incident.id] = incident
        self._verifications[incident.id] = [payload.confidence]
        return incident

    def get(self, incident_id: str) -> Optional[Incident]:
        return self._incidents.get(incident_id)

    def list(self, status: Optional[IncidentStatus] = None) -> List[Incident]:
        vals = list(self._incidents.values())
        if status:
            vals = [i for i in vals if i.status == status]
        return sorted(vals, key=lambda i: i.reported_at, reverse=True)

    def add_verification(self, incident_id: str, confidence: float) -> Optional[Incident]:
        incident = self._incidents.get(incident_id)
        if not incident or incident.status != IncidentStatus.pending:
            return incident
        self._verifications[incident_id].append(confidence)
        incident.verification_count = len(self._verifications[incident_id])
        avg_conf = sum(self._verifications[incident_id]) / len(self._verifications[incident_id])

        if incident.verification_count >= CONFIRM_VERIFICATIONS_NEEDED and avg_conf >= CONFIRM_MIN_CONFIDENCE:
            incident.status = IncidentStatus.confirmed
            incident.confirmed_at = datetime.now(timezone.utc)
            latency = (incident.confirmed_at - incident.reported_at).total_seconds() * 1000
            self._latencies_ms.append(latency)
            drivers = self.nearby_drivers(incident.lat, incident.lng, ALERT_RADIUS_KM)
            incident.alerted_driver_count = len(drivers)
            self.alerts_sent_today += len(drivers)
        return incident

    def clear(self, incident_id: str) -> Optional[Incident]:
        incident = self._incidents.get(incident_id)
        if incident:
            incident.status = IncidentStatus.cleared
            incident.cleared_at = datetime.now(timezone.utc)
        return incident

    # ---- nearby drivers (stub — a real deployment queries live GPS pings) ----
    def nearby_drivers(self, lat: float, lng: float, radius_km: float) -> List[NearbyDriver]:
        rng = random.Random(f"{lat:.3f}:{lng:.3f}")
        count = rng.randint(6, 14)
        drivers = []
        for i in range(count):
            dist = rng.uniform(0.3, radius_km)
            bearing = rng.uniform(0, 2 * math.pi)
            dlat = (dist / 111.0) * math.cos(bearing)
            dlng = (dist / (111.0 * math.cos(math.radians(lat)))) * math.sin(bearing)
            speed_kmh = rng.uniform(40, 90)
            drivers.append(NearbyDriver(
                driver_id=f"veh-{1000 + i}",
                lat=lat + dlat, lng=lng + dlng,
                distance_km=round(dist, 2),
                eta_seconds=int(dist / speed_kmh * 3600),
            ))
        return sorted(drivers, key=lambda d: d.distance_km)

    # ---- stats ----
    def stats(self) -> Stats:
        active = len([i for i in self._incidents.values() if i.status == IncidentStatus.confirmed])
        avg_latency = sum(self._latencies_ms) / len(self._latencies_ms) if self._latencies_ms else None
        return Stats(
            active_incidents=active,
            alerts_sent_today=self.alerts_sent_today,
            avg_latency_ms=avg_latency,
            vehicles_connected=random.randint(380, 460),
        )


store = IncidentStore()
