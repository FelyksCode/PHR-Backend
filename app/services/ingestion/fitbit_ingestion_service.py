from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import pytz
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.vendor_integration import VendorIntegration
from app.services.fitbit_service import fitbit_service
from app.services.fhir_mapper import fhir_mapper
from app.services.ingestion.dtos import NormalizedObservationDTO


class FitbitIngestionService:
    vendor = "fitbit"

    async def ingest(
        self,
        db: Session,
        user: User,
        integration: VendorIntegration,
        after_datetime: Optional[datetime],
    ) -> Dict[str, Any]:
        """Ingest Fitbit data and persist as FHIR Observations.

        - Pulls vendor data incrementally based on after_datetime
        - Normalizes to internal DTOs
        - Converts DTOs to FHIR Observation resources
        - Persists to HAPI FHIR (idempotent conditional create)
        """

        if not user.fhir_patient_id:
            return {
                "success": False,
                "observations_created": 0,
                "observations_skipped": 0,
                "errors": ["User does not have a FHIR patient ID"],
            }

        utc = pytz.UTC
        now_utc = datetime.now(utc)

        # Determine day range to fetch.
        # Fitbit endpoints in this codebase are day-scoped, so we do a day-by-day
        # incremental sync starting from after_datetime's date.
        if after_datetime is None:
            start_date = now_utc.date()
        else:
            if after_datetime.tzinfo is None:
                after_datetime = utc.localize(after_datetime)
            start_date = after_datetime.astimezone(utc).date()

        end_date = now_utc.date()

        normalized: List[NormalizedObservationDTO] = []
        day = start_date
        while day <= end_date:
            data = await fitbit_service.fetch_all_health_data(db=db, user_id=user.id, date_str=day.isoformat())
            normalized.extend(self._normalize_day(data, day=day, user_timezone=user.timezone or "UTC"))
            day += timedelta(days=1)

        # Filter strictly newer than after_datetime if provided.
        if after_datetime is not None:
            normalized = [dto for dto in normalized if dto.effective_datetime > after_datetime]

        # Convert DTOs to FHIR Observations with a stable idempotency key.
        observations = []
        for dto in normalized:
            identifier_value = self._dedupe_identifier(
                patient_id=user.fhir_patient_id,
                observation_type=dto.observation_type,
                effective_datetime=dto.effective_datetime,
                vendor_source_id=dto.vendor_source_id,
            )
            obs = fhir_mapper.create_observation(
                patient_id=user.fhir_patient_id,
                observation_type=dto.observation_type,
                value=float(dto.value),
                unit=dto.unit,
                effective_datetime=dto.effective_datetime,
                additional_data=(dto.additional_data or {}),
                user_timezone=user.timezone or "UTC",
                identifier_override=identifier_value,
            )
            observations.append(obs)

        post_result = await fhir_mapper.post_observations_to_fhir(observations)
        return {
            "success": post_result["failed"] == 0,
            "observations_created": post_result.get("created", post_result.get("success", 0)),
            "observations_skipped": post_result.get("skipped", 0),
            "errors": post_result.get("errors", []),
        }

    def _dedupe_identifier(
        self,
        patient_id: str,
        observation_type: str,
        effective_datetime: datetime,
        vendor_source_id: str,
    ) -> str:
        # Required dedupe dimensions: vendor source ID + timestamp + observation type.
        # We embed patient_id so identifiers are unique per patient, too.
        if effective_datetime.tzinfo is None:
            effective_datetime = pytz.UTC.localize(effective_datetime)
        ts = effective_datetime.astimezone(pytz.UTC).strftime("%Y%m%d%H%M%S")
        return f"{self.vendor}-{patient_id}-{observation_type}-{ts}-{vendor_source_id}"

    def _normalize_day(
        self,
        fitbit_data: Dict[str, Any],
        day: date,
        user_timezone: str,
    ) -> List[NormalizedObservationDTO]:
        """Normalize the day's Fitbit responses into vendor-agnostic DTOs."""

        tz = pytz.timezone(user_timezone) if user_timezone else pytz.UTC
        day_str = day.isoformat()
        out: List[NormalizedObservationDTO] = []

        # Heart rate intraday (sample every 2 hours to match existing behavior)
        hr = fitbit_data.get("heart_rate") or {}
        dataset = hr.get("activities-heart-intraday", {}).get("dataset", [])
        if dataset:
            for dp in dataset:
                time_str = dp.get("time")
                value = dp.get("value")
                if not time_str or value is None:
                    continue
                hour = int(time_str.split(":")[0])
                if hour % 2 != 0:
                    continue
                dt = datetime.fromisoformat(f"{day_str}T{time_str}")
                if dt.tzinfo is None:
                    dt = tz.localize(dt)
                out.append(
                    NormalizedObservationDTO(
                        vendor=self.vendor,
                        observation_type="heart_rate",
                        effective_datetime=dt,
                        value=float(value),
                        unit="beats/min",
                        vendor_source_id=f"heart_rate:{day_str}:{time_str}",
                        additional_data={"type": "intraday"},
                    )
                )

        # SpO2 daily avg
        spo2 = fitbit_data.get("spo2") or {}
        avg = (spo2.get("value") or {}).get("avg")
        if avg is not None:
            dt = datetime.now(tz)
            out.append(
                NormalizedObservationDTO(
                    vendor=self.vendor,
                    observation_type="spo2",
                    effective_datetime=dt,
                    value=float(avg),
                    unit="%",
                    vendor_source_id=f"spo2:{day_str}",
                    additional_data={
                        "min": (spo2.get("value") or {}).get("min"),
                        "max": (spo2.get("value") or {}).get("max"),
                    },
                )
            )

        # Weight logs
        weight = fitbit_data.get("body_weight") or {}
        for log in weight.get("weight", []) or []:
            w = log.get("weight")
            if w is None:
                continue
            date_s = log.get("date") or day_str
            time_s = log.get("time")
            if time_s:
                dt = datetime.fromisoformat(f"{date_s}T{time_s}")
                if dt.tzinfo is None:
                    dt = tz.localize(dt)
            else:
                dt = datetime.now(tz)
            log_id = log.get("logId")
            vendor_source_id = f"weight:{log_id}" if log_id is not None else f"weight:{date_s}:{time_s or 'na'}"
            out.append(
                NormalizedObservationDTO(
                    vendor=self.vendor,
                    observation_type="body_weight",
                    effective_datetime=dt,
                    value=float(w),
                    unit="kg",
                    vendor_source_id=vendor_source_id,
                    additional_data={"bmi": log.get("bmi"), "source": log.get("source")},
                )
            )

        # Calories intraday (keep latest of the day)
        calories = fitbit_data.get("calories_timeseries") or {}
        c_dataset = calories.get("activities-calories-intraday", {}).get("dataset", [])
        if c_dataset:
            latest = next((dp for dp in reversed(c_dataset) if dp.get("value") is not None), None)
            if latest:
                time_str = latest.get("time")
                value = latest.get("value")
                if time_str and value is not None:
                    dt = datetime.fromisoformat(f"{day_str}T{time_str}")
                    if dt.tzinfo is None:
                        dt = tz.localize(dt)
                    out.append(
                        NormalizedObservationDTO(
                            vendor=self.vendor,
                            observation_type="calories",
                            effective_datetime=dt,
                            value=float(value),
                            unit="kcal",
                            vendor_source_id=f"calories:{day_str}",
                            additional_data={"type": "daily_latest"},
                        )
                    )

        return out
