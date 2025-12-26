"""
FHIR Observation mapper service
Converts vendor health data to FHIR Observation resources
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import httpx

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
        additional_data: Optional[Dict[str, Any]] = None
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
            
        Returns:
            FHIR Observation resource as dict
        """
        if observation_type not in self.LOINC_CODES:
            raise ValueError(f"Unsupported observation type: {observation_type}")
        
        loinc = self.LOINC_CODES[observation_type]
        
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
            "issued": datetime.utcnow().isoformat(),
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
        last_sync_datetime: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Map Fitbit heart rate data to FHIR Observations
        
        Args:
            patient_id: FHIR Patient ID
            fitbit_data: Raw Fitbit heart rate response
            last_sync_datetime: Last sync datetime to use for effectiveDateTime
            
        Returns:
            List of FHIR Observation resources
        """
        observations = []
        
        try:
            activities_heart = fitbit_data.get("activities-heart", [])
            if not activities_heart:
                return observations
            
            for day_data in activities_heart:
                date_str = day_data.get("dateTime")
                value_data = day_data.get("value", {})
                
                # Resting heart rate
                resting_hr = value_data.get("restingHeartRate")
                if resting_hr:
                    # Use last_sync_datetime if available, otherwise use data date
                    effective_dt = last_sync_datetime if last_sync_datetime else datetime.fromisoformat(date_str)
                    obs = self.create_observation(
                        patient_id=patient_id,
                        observation_type="heart_rate",
                        value=float(resting_hr),
                        unit="beats/min",
                        effective_datetime=effective_dt,
                        additional_data={"type": "resting"}
                    )
                    observations.append(obs)
                
                # Heart rate zones (optional, creating observations for each zone)
                heart_rate_zones = value_data.get("heartRateZones", [])
                for zone in heart_rate_zones:
                    if zone.get("minutes", 0) > 0:
                        # Create observation for time in zone
                        zone_name = zone.get("name")
                        minutes = zone.get("minutes")
                        logger.debug(f"Heart rate zone {zone_name}: {minutes} minutes")
        
        except Exception as e:
            logger.error(f"Error mapping Fitbit heart rate data: {str(e)}")
        
        return observations
    
    def map_fitbit_spo2(
        self,
        patient_id: str,
        fitbit_data: Dict[str, Any],
        last_sync_datetime: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Map Fitbit SpO2 data to FHIR Observations
        
        Args:
            patient_id: FHIR Patient ID
            fitbit_data: Raw Fitbit SpO2 response
            last_sync_datetime: Last sync datetime to use for effectiveDateTime
            
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
                # Use last_sync_datetime if available, otherwise use data date
                effective_dt = last_sync_datetime if last_sync_datetime else datetime.fromisoformat(date_str)
                obs = self.create_observation(
                    patient_id=patient_id,
                    observation_type="spo2",
                    value=float(avg_spo2),
                    unit="%",
                    effective_datetime=effective_dt,
                    additional_data={
                        "min": value_data.get("min"),
                        "max": value_data.get("max")
                    }
                )
                observations.append(obs)
        
        except Exception as e:
            logger.error(f"Error mapping Fitbit SpO2 data: {str(e)}")
        
        return observations
    
    def map_fitbit_weight(
        self,
        patient_id: str,
        fitbit_data: Dict[str, Any],
        last_sync_datetime: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Map Fitbit weight data to FHIR Observations
        
        Args:
            patient_id: FHIR Patient ID
            fitbit_data: Raw Fitbit weight response
            last_sync_datetime: Last sync datetime to use for effectiveDateTime
            
        Returns:
            List of FHIR Observation resources
        """
        observations = []
        
        try:
            weight_logs = fitbit_data.get("weight", [])
            
            for log in weight_logs:
                weight = log.get("weight")
                date_str = log.get("date")
                time_str = log.get("time")
                
                if weight and date_str:
                    # Use last_sync_datetime if available, otherwise use data date/time
                    if last_sync_datetime:
                        effective_dt = last_sync_datetime
                    else:
                        datetime_str = f"{date_str}T{time_str}" if time_str else date_str
                        effective_dt = datetime.fromisoformat(datetime_str)
                    
                    obs = self.create_observation(
                        patient_id=patient_id,
                        observation_type="body_weight",
                        value=float(weight),
                        unit="kg",
                        effective_datetime=effective_dt,
                        additional_data={
                            "bmi": log.get("bmi"),
                            "source": log.get("source")
                        }
                    )
                    observations.append(obs)
        
        except Exception as e:
            logger.error(f"Error mapping Fitbit weight data: {str(e)}")
        
        return observations
    
    def map_fitbit_activity(
        self,
        patient_id: str,
        fitbit_data: Dict[str, Any],
        last_sync_datetime: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Map Fitbit activity data to FHIR Observations
        
        Args:
            patient_id: FHIR Patient ID
            fitbit_data: Raw Fitbit activity response
            last_sync_datetime: Last sync datetime to use for effectiveDateTime
            
        Returns:
            List of FHIR Observation resources
        """
        observations = []
        
        try:
            summary = fitbit_data.get("summary", {})
            date_str = fitbit_data.get("activities", [{}])[0].get("startDate") if fitbit_data.get("activities") else None
            
            # Use last_sync_datetime if available, otherwise use data date
            if last_sync_datetime:
                effective_dt = last_sync_datetime
            else:
                if not date_str:
                    # Use current date as fallback
                    date_str = datetime.now().date().isoformat()
                effective_dt = datetime.fromisoformat(date_str)
            
            # Steps
            steps = summary.get("steps")
            if steps:
                obs = self.create_observation(
                    patient_id=patient_id,
                    observation_type="steps",
                    value=float(steps),
                    unit="steps",
                    effective_datetime=effective_dt
                )
                observations.append(obs)
            
            # Calories
            calories = summary.get("caloriesOut")
            if calories:
                obs = self.create_observation(
                    patient_id=patient_id,
                    observation_type="calories",
                    value=float(calories),
                    unit="kcal",
                    effective_datetime=effective_dt
                )
                observations.append(obs)
            
            # Distance
            distances = summary.get("distances", [])
            for distance in distances:
                if distance.get("activity") == "total":
                    dist_value = distance.get("distance")
                    if dist_value:
                        obs = self.create_observation(
                            patient_id=patient_id,
                            observation_type="distance",
                            value=float(dist_value),
                            unit="km",
                            effective_datetime=effective_dt
                        )
                        observations.append(obs)
                        break
        
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
        Post FHIR Observations to HAPI FHIR server
        
        Args:
            observations: List of FHIR Observation resources
            
        Returns:
            Summary of posted observations
        """
        results = {
            "total": len(observations),
            "success": 0,
            "failed": 0,
            "errors": []
        }
        
        async with httpx.AsyncClient() as client:
            for obs in observations:
                try:
                    response = await client.post(
                        f"{settings.fhir_base_url}/Observation",
                        json=obs,
                        headers={"Content-Type": "application/fhir+json"},
                        timeout=30.0
                    )
                    
                    if response.status_code in [200, 201]:
                        results["success"] += 1
                        logger.debug(f"Successfully posted observation: {obs.get('code', {}).get('text')}")
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
        
        return results


fhir_mapper = FHIRMapper()
