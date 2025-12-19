"""
Background sync service for vendor health data
Handles periodic syncing of health data from vendors to FHIR server
"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any
import logging

from app.services.fitbit_service import fitbit_service, FitbitAPIError
from app.services.fhir_mapper import fhir_mapper
from app.services.vendor_integration_service import vendor_integration_service
from app.models.user import User

logger = logging.getLogger(__name__)


class SyncService:
    """
    Service for syncing vendor health data to FHIR server
    """
    
    async def sync_fitbit_data(
        self,
        db: Session,
        user: User,
        date_str: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sync Fitbit data for a user to FHIR server
        
        Args:
            db: Database session
            user: User object
            date_str: Date to sync (YYYY-MM-DD), defaults to today
            
        Returns:
            Sync summary
        """
        if not date_str:
            date_str = date.today().isoformat()
        
        sync_result = {
            "user_id": user.id,
            "vendor": "fitbit",
            "date": date_str,
            "success": False,
            "observations_created": 0,
            "errors": []
        }
        
        # Check if user has FHIR patient ID
        if not user.fhir_patient_id:
            sync_result["errors"].append("User does not have a FHIR patient ID")
            logger.warning(f"User {user.id} does not have FHIR patient ID")
            return sync_result
        
        try:
            # Fetch Fitbit data
            logger.info(f"Fetching Fitbit data for user {user.id} on {date_str}")
            fitbit_data = await fitbit_service.fetch_all_health_data(
                db=db,
                user_id=user.id,
                date_str=date_str
            )
            
            # Map to FHIR Observations
            all_observations = []
            
            # Heart rate
            if fitbit_data.get("heart_rate"):
                hr_obs = fhir_mapper.map_fitbit_heart_rate(
                    patient_id=user.fhir_patient_id,
                    fitbit_data=fitbit_data["heart_rate"]
                )
                all_observations.extend(hr_obs)
                logger.debug(f"Mapped {len(hr_obs)} heart rate observations")
            
            # SpO2
            if fitbit_data.get("spo2"):
                spo2_obs = fhir_mapper.map_fitbit_spo2(
                    patient_id=user.fhir_patient_id,
                    fitbit_data=fitbit_data["spo2"]
                )
                all_observations.extend(spo2_obs)
                logger.debug(f"Mapped {len(spo2_obs)} SpO2 observations")
            
            # Weight
            if fitbit_data.get("body_weight"):
                weight_obs = fhir_mapper.map_fitbit_weight(
                    patient_id=user.fhir_patient_id,
                    fitbit_data=fitbit_data["body_weight"]
                )
                all_observations.extend(weight_obs)
                logger.debug(f"Mapped {len(weight_obs)} weight observations")
            
            # Activity
            if fitbit_data.get("activity_summary"):
                activity_obs = fhir_mapper.map_fitbit_activity(
                    patient_id=user.fhir_patient_id,
                    fitbit_data=fitbit_data["activity_summary"]
                )
                all_observations.extend(activity_obs)
                logger.debug(f"Mapped {len(activity_obs)} activity observations")
            
            # Post to FHIR server
            if all_observations:
                logger.info(f"Posting {len(all_observations)} observations to FHIR server")
                post_result = await fhir_mapper.post_observations_to_fhir(all_observations)
                
                sync_result["observations_created"] = post_result["success"]
                sync_result["success"] = post_result["success"] > 0
                
                if post_result["errors"]:
                    sync_result["errors"].extend(post_result["errors"])
            else:
                sync_result["success"] = True
                sync_result["errors"].append("No health data available for the specified date")
            
            # Update last sync timestamp
            integration = vendor_integration_service.get_integration(
                db=db,
                user_id=user.id,
                vendor="fitbit"
            )
            if integration:
                vendor_integration_service.update_last_sync(db, integration.id)
        
        except FitbitAPIError as e:
            sync_result["errors"].append(f"Fitbit API error: {str(e)}")
            logger.error(f"Fitbit API error during sync: {str(e)}")
        except Exception as e:
            sync_result["errors"].append(f"Unexpected error: {str(e)}")
            logger.error(f"Error during Fitbit sync: {str(e)}", exc_info=True)
        
        return sync_result
    
    async def sync_user_vendors(
        self,
        db: Session,
        user_id: int,
        date_str: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sync all active vendor integrations for a user
        
        Args:
            db: Database session
            user_id: User ID
            date_str: Date to sync (YYYY-MM-DD), defaults to today
            
        Returns:
            Sync summary for all vendors
        """
        from app.services.user_service import user_service
        
        user = user_service.get_user_by_id(db, user_id)
        if not user:
            return {
                "success": False,
                "error": "User not found"
            }
        
        integrations = vendor_integration_service.get_user_integrations(
            db=db,
            user_id=user_id,
            active_only=True
        )
        
        results = {
            "user_id": user_id,
            "date": date_str or date.today().isoformat(),
            "vendors": []
        }
        
        for integration in integrations:
            if integration.vendor == "fitbit":
                result = await self.sync_fitbit_data(db, user, date_str)
                results["vendors"].append(result)
            else:
                logger.warning(f"Unsupported vendor: {integration.vendor}")
        
        return results


sync_service = SyncService()
