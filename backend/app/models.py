"""Pydantic schemas shared across the RoadAlert API.

These mirror the "event packet" described in the project's architecture
slide: a vehicle only ever sends location, heading, confidence and an
incident type — never raw video.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class IncidentType(str, Enum):
    collision = "collision"
    stopped_vehicle = "stopped_vehicle"
    fire = "fire"
    debris = "debris"


class IncidentStatus(str, Enum):
    pending = "pending"       # reported by one vehicle, not yet verified
    confirmed = "confirmed"   # verified, alerts have gone out
    cleared = "cleared"       # road is normal again


class IncidentCreate(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    heading_deg: float = Field(..., ge=0, lt=360, description="Compass heading of the reporting vehicle")
    speed_kmh: Optional[float] = Field(default=None, ge=0)
    confidence: float = Field(..., ge=0, le=1, description="On-device model's confidence score")
    incident_type: IncidentType = IncidentType.collision
    vehicle_id: Optional[str] = Field(default=None, description="Opaque per-device id, never a personal identifier")


class VerificationCreate(BaseModel):
    vehicle_id: Optional[str] = None
    confidence: float = Field(..., ge=0, le=1)
    source: str = Field(default="vehicle", description="'vehicle' or 'authority'")


class Incident(BaseModel):
    id: str
    lat: float
    lng: float
    heading_deg: float
    incident_type: IncidentType
    status: IncidentStatus
    confidence: float
    verification_count: int = 0
    reported_at: datetime
    confirmed_at: Optional[datetime] = None
    cleared_at: Optional[datetime] = None
    alerted_driver_count: int = 0


class NearbyDriver(BaseModel):
    driver_id: str
    lat: float
    lng: float
    distance_km: float
    eta_seconds: int


class Stats(BaseModel):
    active_incidents: int
    alerts_sent_today: int
    avg_latency_ms: Optional[float]
    vehicles_connected: int
