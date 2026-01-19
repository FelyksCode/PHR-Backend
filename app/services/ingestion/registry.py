from __future__ import annotations

from typing import Dict

from app.services.ingestion.fitbit_ingestion_service import FitbitIngestionService


class IngestionRegistry:
    """Maps vendor keys to ingestion services."""

    def __init__(self) -> None:
        self._services = {
            "fitbit": FitbitIngestionService(),
        }

    def get(self, vendor: str):
        vendor_key = (vendor or "").lower().strip()
        if vendor_key not in self._services:
            raise KeyError(f"Unsupported vendor: {vendor_key}")
        return self._services[vendor_key]

    def supported_vendors(self):
        return sorted(self._services.keys())


ingestion_registry = IngestionRegistry()
