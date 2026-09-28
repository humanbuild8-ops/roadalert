"""Tiny client for the RoadAlert backend (../backend). Never crashes the detector
if the backend is down: it just prints a warning."""
import requests


class BackendClient:
    def __init__(self, base_url="http://localhost:8000", lat=12.9716, lng=77.5946, heading=15.0, timeout=3):
        self.base = base_url.rstrip("/")
        self.lat, self.lng, self.heading, self.timeout = lat, lng, heading, timeout

    def report(self, confidence, incident_type="collision"):
        body = dict(lat=self.lat, lng=self.lng, heading_deg=self.heading,
                    confidence=float(confidence), incident_type=incident_type)
        try:
            r = requests.post(f"{self.base}/api/incidents", json=body, timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"[warn] could not reach backend: {e}")
            return None

    def verify(self, incident_id, confidence, source="vehicle"):
        try:
            r = requests.post(f"{self.base}/api/incidents/{incident_id}/verify",
                              json=dict(confidence=float(confidence), source=source), timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"[warn] verify failed: {e}")
            return None
