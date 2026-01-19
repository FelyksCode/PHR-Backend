"""
FHIR Observation mapper service
Converts vendor health data to FHIR Observation resources
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import httpx
import pytz

from app.config import settings

logger = logging.getLogger(__name__)


class FHIRMapper:
    """
    Maps vendor health data to FHIR Observation resources
    Following HL7 FHIR R4 specification
    """
    
    # LOINC codes for common observations
    LOINC_CODES = {
        "heart_rate": {
            "code": "8867-4",
            "display": "Heart rate",
            "system": "http://loinc.org"
        },
        "spo2": {
            "code": "59408-5",
            "display": "Oxygen saturation in Arterial blood by Pulse oximetry",
            "system": "http://loinc.org"
        },
        "body_weight": {
            "code": "29463-7",
            "display": "Body weight",
            "system": "http://loinc.org"
        },
        "steps": {
            "code": "41950-7",
            "display": "Number of steps in 24 hour Measured",
            "system": "http://loinc.org"
        },
        "calories": {
            "code": "41981-2",
            "display": "Calories burned",
            "system": "http://loinc.org"
        },
        "distance": {
            "code": "41953-1",
            "display": "Distance walked or run",
            "system": "http://loinc.org"
        },
        "blood_pressure": {
            "code": "35094-2",
            "display": "Blood Pressure Panel",
            "system": "http://loinc.org"
        }
    }
    
    def create_observation(
        self,
        patient_id: str,
        observation_type: str,
        value: float,
        unit: str,
        effective_datetime: datetime,
        additional_data: Optional[Dict[str, Any]] = None,
        user_timezone: str = "UTC",
        identifier_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a FHIR Observation resource
        
        Args:
            patient_id: FHIR Patient ID
            observation_type: Type of observation (e.g., "heart_rate", "spo2")
            value: Numeric value of the observation
            unit: Unit of measurement
            effective_datetime: When the observation was made
            additional_data: Additional metadata
            user_timezone: User's timezone (default: UTC)
            identifier_override: Custom identifier value to allow day-level upserts
            
        Returns:
            FHIR Observation resource as dict
        """
        if observation_type not in self.LOINC_CODES:
            raise ValueError(f"Unsupported observation type: {observation_type}")
        
        loinc = self.LOINC_CODES[observation_type]
        
        # Convert to user's timezone for identifier
        try:
            tz = pytz.timezone(user_timezone)
            if effective_datetime.tzinfo is None:
                effective_datetime = pytz.UTC.localize(effective_datetime)
            effective_datetime_local = effective_datetime.astimezone(tz)
        except:
            effective_datetime_local = effective_datetime
        
        # Create a unique identifier to prevent duplicates
        # Format: fitbit-{patient_id}-{observation_type}-{date}-{additional_key}
        effective_date = effective_datetime_local.strftime("%Y%m%d%H%M%S")
        additional_key = additional_data.get("type", "") if additional_data else ""
        if identifier_override:
            identifier_value = identifier_override
        else:
            identifier_value = f"fitbit-{patient_id}-{observation_type}-{effective_date}"
            if additional_key:
                identifier_value += f"-{additional_key}"
        
        observation = {
            "resourceType": "Observation",
            "identifier": [{
                "system": "http://phr-system.com/observation-id",
                "value": identifier_value
            }],
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "vital-signs",
                    "display": "Vital Signs"
                }]
            }],
            "code": {
                "coding": [{
                    "system": loinc["system"],
                    "code": loinc["code"],
                    "display": loinc["display"]
                }],
                "text": loinc["display"]
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            },
            "effectiveDateTime": effective_datetime.isoformat(),
            "issued": datetime.now(pytz.timezone(user_timezone)).isoformat(),
            "valueQuantity": {
                "value": value,
                "unit": unit,
                "system": "http://unitsofmeasure.org",
                "code": unit
            }
        }
        
        # Add additional metadata if provided
        if additional_data:
            observation["note"] = [{
                "text": f"Source: Fitbit. Additional data: {str(additional_data)}"
            }]
        
        return observation
    
    def map_fitbit_heart_rate(
        self,
        patient_id: str,
        fitbit_data: Dict[str, Any],
        last_sync_datetime: Optional[datetime] = None,
        user_timezone: str = "UTC"
    ) -> List[Dict[str, Any]]:
        """
        Map Fitbit heart rate intraday data to FHIR Observations
        Samples data every 2 hours to reduce volume
        
        Args:
            patient_id: FHIR Patient ID
            fitbit_data: Raw Fitbit heart rate intraday response
            last_sync_datetime: Last sync datetime to filter newer data
            user_timezone: User's timezone
            
        Returns:
            List of FHIR Observation resources
        """
        observations = []
        
        try:
            # Check for intraday data first
            intraday_dataset = fitbit_data.get("activities-heart-intraday", {}).get("dataset", [])
            
            if intraday_dataset:
                # Process intraday data with actual timestamps
                activities_heart = fitbit_data.get("activities-heart", [])
                date_str = activities_heart[0].get("dateTime") if activities_heart else None
                
                if date_str:
                    # Sample every 2 hours (keep observations at 00:00, 02:00, 04:00, 06:00, etc.)
                    for datapoint in intraday_dataset:
                        time_str = datapoint.get("time")  # Format: "HH:MM:SS"
                        value = datapoint.get("value")
                        
                        if time_str and value:
                            # Parse hour from time string
                            hour = int(time_str.split(":")[0])
                            
                            # Only keep data points at 2-hour intervals (0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22)
                            if hour % 2 != 0:
                                continue
                            
                            # Combine date and time to get full timestamp
                            datetime_str = f"{date_str}T{time_str}"
                            effective_dt = datetime.fromisoformat(datetime_str)
                            
                            # Skip if before last sync
                            if last_sync_datetime and effective_dt <= last_sync_datetime:
                                continue
                            
                            obs = self.create_observation(
                                patient_id=patient_id,
                                observation_type="heart_rate",
                                value=float(value),
                                unit="beats/min",
                                effective_datetime=effective_dt,
                                additional_data={"type": "intraday"},
                                user_timezone=user_timezone
                            )
                            observations.append(obs)
            else:
                # Fallback to daily summary if intraday not available
                activities_heart = fitbit_data.get("activities-heart", [])
                if not activities_heart:
                    return observations
                
                for day_data in activities_heart:
                    date_str = day_data.get("dateTime")
                    value_data = day_data.get("value", {})
                    
                    # Resting heart rate
                    resting_hr = value_data.get("restingHeartRate")
                    if resting_hr and date_str:
                        effective_dt = datetime.now(pytz.timezone(user_timezone))
                        obs = self.create_observation(
                            patient_id=patient_id,
                            observation_type="heart_rate",
                            value=float(resting_hr),
                            unit="beats/min",
                            effective_datetime=effective_dt,
                            additional_data={"type": "resting"},
                            user_timezone=user_timezone
                        )
                        observations.append(obs)
        
        except Exception as e:
            logger.error(f"Error mapping Fitbit heart rate data: {str(e)}")
        
        return observations
    
    def map_fitbit_spo2(
        self,
        patient_id: str,
        fitbit_data: Dict[str, Any],
        last_sync_datetime: Optional[datetime] = None,
        user_timezone: str = "UTC"
    ) -> List[Dict[str, Any]]:
        """
        Map Fitbit SpO2 data to FHIR Observations
        
        Args:
            patient_id: FHIR Patient ID
            fitbit_data: Raw Fitbit SpO2 response
            last_sync_datetime: Last sync datetime to use for effectiveDateTime
            user_timezone: User's timezone
            
        Returns:
            List of FHIR Observation resources
        """
        observations = []
        
        try:
            # Fitbit SpO2 data structure
            date_str = fitbit_data.get("dateTime")
            value_data = fitbit_data.get("value", {})
            avg_spo2 = value_data.get("avg")
            
            if avg_spo2 and date_str:
                # Use user's timezone for the timestamp
                tz = pytz.timezone(user_timezone)
                effective_dt = datetime.now(tz)
                obs = self.create_observation(
                    patient_id=patient_id,
                    observation_type="spo2",
                    value=float(avg_spo2),
                    unit="%",
                    effective_datetime=effective_dt,
                    additional_data={
                        "min": value_data.get("min"),
                        "max": value_data.get("max")
                    },
                    user_timezone=user_timezone
                )
                observations.append(obs)
        
        except Exception as e:
            logger.error(f"Error mapping Fitbit SpO2 data: {str(e)}")
        
        return observations
    
    def map_fitbit_weight(
        self,
        patient_id: str,
        fitbit_data: Dict[str, Any],
        last_sync_datetime: Optional[datetime] = None,
        user_timezone: str = "UTC"
    ) -> List[Dict[str, Any]]:
        """
        Map Fitbit weight data to FHIR Observations
        
        Args:
            patient_id: FHIR Patient ID
            fitbit_data: Raw Fitbit weight response
            last_sync_datetime: Last sync datetime to use for effectiveDateTime
            user_timezone: User's timezone
            
        Returns:
            List of FHIR Observation resources
        """
        observations = []
        
        try:
            weight_logs = fitbit_data.get("weight", [])
            tz = pytz.timezone(user_timezone)
            
            for log in weight_logs:
                weight = log.get("weight")
                date_str = log.get("date")
                time_str = log.get("time")
                
                if weight and date_str:
                    # Use actual timestamp if available, otherwise use current time in user's timezone
                    if time_str:
                        datetime_str = f"{date_str}T{time_str}"
                        effective_dt = datetime.fromisoformat(datetime_str)
                        # Make it aware of user's timezone
                        if effective_dt.tzinfo is None:
                            effective_dt = tz.localize(effective_dt)
                    else:
                        effective_dt = datetime.now(tz)
                    
                    obs = self.create_observation(
                        patient_id=patient_id,
                        observation_type="body_weight",
                        value=float(weight),
                        unit="kg",
                        effective_datetime=effective_dt,
                        additional_data={
                            "bmi": log.get("bmi"),
                            "source": log.get("source")
                        },
                        user_timezone=user_timezone
                    )
                    observations.append(obs)
        
        except Exception as e:
            logger.error(f"Error mapping Fitbit weight data: {str(e)}")
        
        return observations
    
    def map_fitbit_calories_timeseries(
        self,
        patient_id: str,
        fitbit_data: Dict[str, Any],
        last_sync_datetime: Optional[datetime] = None,
        user_timezone: str = "UTC"
    ) -> List[Dict[str, Any]]:
        """
        Map Fitbit calories intraday data to FHIR Observations
        Persist only the latest value per day and upsert by day-level identifier
        
        Args:
            patient_id: FHIR Patient ID
            fitbit_data: Raw Fitbit calories intraday response
            last_sync_datetime: Last sync datetime to filter newer data
            user_timezone: User's timezone
            
        Returns:
            List of FHIR Observation resources
        """
        observations = []
        
        try:
            # Check for intraday data first
            intraday_dataset = fitbit_data.get("activities-calories-intraday", {}).get("dataset", [])
            
            if intraday_dataset:
                activities_calories = fitbit_data.get("activities-calories", [])
                date_str = activities_calories[0].get("dateTime") if activities_calories else None
                
                if date_str:
                    # Get the latest non-null datapoint for the day
                    latest_datapoint = next(
                        (dp for dp in reversed(intraday_dataset) if dp.get("value") is not None),
                        None
                    )
                    if latest_datapoint:
                        time_str = latest_datapoint.get("time")
                        value = latest_datapoint.get("value")
                        if time_str and value is not None:
                            datetime_str = f"{date_str}T{time_str}"
                            effective_dt = datetime.fromisoformat(datetime_str)
                            identifier_override = f"fitbit-{patient_id}-calories-{date_str}-daily"
                            obs = self.create_observation(
                                patient_id=patient_id,
                                observation_type="calories",
                                value=float(value),
                                unit="kcal",
                                effective_datetime=effective_dt,
                                user_timezone=user_timezone,
                                identifier_override=identifier_override
                            )
                           
                            observations.append(obs)
            else:
                # Fallback to daily summary
                items = fitbit_data.get("activities-calories", [])
                for item in items:
                    date_str = item.get("dateTime")
                    value_str = item.get("value")
                    if date_str and value_str is not None:
                        try:
                            value = float(value_str)
                        except (TypeError, ValueError):
                            continue
                        effective_dt = datetime.now(pytz.timezone(user_timezone))
                        identifier_override = f"fitbit-{patient_id}-calories-{date_str}-daily"
                        obs = self.create_observation(
                            patient_id=patient_id,
                            observation_type="calories",
                            value=value,
                            unit="kcal",
                            effective_datetime=effective_dt,
                            user_timezone=user_timezone,
                            identifier_override=identifier_override
                        ) 
                        observations.append(obs)
        except Exception as e:
            logger.error(f"Error mapping Fitbit calories timeseries: {str(e)}")
        
        return observations
    
    def map_fitbit_activity(
        self,
        patient_id: str,
        fitbit_data: Dict[str, Any],
        last_sync_datetime: Optional[datetime] = None,
        user_timezone: str = "UTC"
    ) -> List[Dict[str, Any]]:
        """
        Map Fitbit activity data (daily total steps) to FHIR Observations
        
        Args:
            patient_id: FHIR Patient ID
            fitbit_data: Raw Fitbit activity summary response
            last_sync_datetime: Last sync datetime (not used for daily summary)
            user_timezone: User's timezone
            
        Returns:
            List of FHIR Observation resources
        """
        observations = []
        
        try:
            # Use daily summary for total steps
            summary = fitbit_data.get("summary", {})
            effective_dt = datetime.now(pytz.timezone(user_timezone))
            
            # Steps - one observation per day
            steps = summary.get("steps")
            if steps and steps > 0:
                obs = self.create_observation(
                    patient_id=patient_id,
                    observation_type="steps",
                    value=float(steps),
                    unit="steps",
                    effective_datetime=effective_dt,
                    user_timezone=user_timezone
                )
                observations.append(obs)
        
        except Exception as e:
            logger.error(f"Error mapping Fitbit activity data: {str(e)}")
        
        return observations
    
    def map_blood_pressure(
        self,
        patient_id: str,
        systolic: float,
        diastolic: float,
        effective_datetime: datetime,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Map blood pressure data to FHIR Observation with component structure
        
        Args:
            patient_id: FHIR Patient ID
            systolic: Systolic blood pressure value
            diastolic: Diastolic blood pressure value
            effective_datetime: When the measurement was taken
            additional_data: Additional metadata
            
        Returns:
            FHIR Observation resource with blood pressure components
        """
        observation = {
            "resourceType": "Observation",
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "vital-signs",
                    "display": "Vital Signs"
                }]
            }],
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "35094-2",
                    "display": "Blood Pressure Panel"
                }],
                "text": "Blood Pressure Panel"
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            },
            "effectiveDateTime": effective_datetime.isoformat(),
            "component": [
                {
                    "code": {
                        "coding": [{
                            "system": "http://loinc.org",
                            "code": "8480-6",
                            "display": "Systolic Blood Pressure"
                        }]
                    },
                    "valueQuantity": {
                        "value": systolic,
                        "unit": "mmHg",
                        "system": "http://unitsofmeasure.org",
                        "code": "mm[Hg]"
                    }
                },
                {
                    "code": {
                        "coding": [{
                            "system": "http://loinc.org",
                            "code": "8462-4",
                            "display": "Diastolic Blood Pressure"
                        }]
                    },
                    "valueQuantity": {
                        "value": diastolic,
                        "unit": "mmHg",
                        "system": "http://unitsofmeasure.org",
                        "code": "mm[Hg]"
                    }
                }
            ]
        }
        
        # Add additional metadata if provided
        if additional_data:
            observation["note"] = [{
                "text": f"Source: Blood Pressure Device. Additional data: {str(additional_data)}"
            }]
        
        return observation
    
    async def post_observations_to_fhir(
        self,
        observations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Post FHIR Observations to HAPI FHIR server using conditional create/update
        to prevent duplicates based on identifier
        
        Args:
            observations: List of FHIR Observation resources
            
        Returns:
            Summary of posted observations
        """
        results = {
            "total": len(observations),
            # created: Observation created
            "created": 0,
            # skipped: Observation already existed (idempotent)
            "skipped": 0,
            "failed": 0,
            "errors": [],
        }
        
        async with httpx.AsyncClient() as client:
            for obs in observations:
                try:
                    headers = {"Content-Type": "application/fhir+json"}

                    # Prefer HAPI conditional create to avoid per-resource search roundtrips.
                    identifier = obs.get("identifier", [])
                    if identifier and len(identifier) > 0:
                        identifier_value = identifier[0].get("value")
                        identifier_system = identifier[0].get("system")
                        if identifier_value and identifier_system:
                            headers["If-None-Exist"] = f"identifier={identifier_system}|{identifier_value}"

                    response = await client.post(
                        f"{settings.fhir_base_url}/Observation",
                        json=obs,
                        headers=headers,
                        timeout=30.0,
                    )

                    # HAPI returns 201 when created; for conditional create, it can return 200 when it matched an existing resource.
                    if response.status_code == 201:
                        results["created"] += 1
                    elif response.status_code == 200:
                        results["skipped"] += 1
                    else:
                        results["failed"] += 1
                        error_msg = f"Failed to post observation: {response.status_code} - {response.text}"
                        results["errors"].append(error_msg)
                        logger.error(error_msg)
                
                except httpx.HTTPError as e:
                    results["failed"] += 1
                    error_msg = f"HTTP error posting observation: {str(e)}"
                    results["errors"].append(error_msg)
                    logger.error(error_msg)
                except Exception as e:
                    results["failed"] += 1
                    error_msg = f"Error posting observation: {str(e)}"
                    results["errors"].append(error_msg)
                    logger.error(error_msg)
        
        # Backward-compatible counters for legacy code paths
        results["success"] = results["created"]
        return results


fhir_mapper = FHIRMapper()
