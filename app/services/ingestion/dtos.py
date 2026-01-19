from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class NormalizedObservationDTO:
    """Vendor-agnostic normalized observation.

    This is the internal DTO boundary between vendor-specific ingestion and
    FHIR persistence.
    """

    vendor: str
    observation_type: str
    effective_datetime: datetime
    value: float
    unit: str

    vendor_source_id: str

    additional_data: Optional[Dict[str, Any]] = None
