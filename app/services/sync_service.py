"""
Background sync service for vendor health data
Handles periodic syncing of health data from vendors to FHIR server
"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any
import logging
import pytz

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
        date_str: Optional[str] = None,
        last_sync_at_override: Optional[datetime] = None,
        update_last_sync: bool = True
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
            # Get integration to access last_sync_at
            integration = vendor_integration_service.get_integration(
                db=db,
                user_id=user.id,
                vendor="fitbit"
            )
            # Allow caller to override last_sync_at when doing multi-day catch-up
            last_sync_at = None
            if integration:
                last_sync_at = last_sync_at_override if last_sync_at_override is not None else integration.last_sync_at
            logger.info(f"LAST SYNC: {last_sync_at}")
            
            # Fetch Fitbit data
            logger.info(f"Fetching Fitbit data for user {user.id} on {date_str}")
            fitbit_data = await fitbit_service.fetch_all_health_data(
                db=db,
                user_id=user.id,
                date_str=date_str
            )
            
            # Debug: Print raw Fitbit responses
            logger.info(f"=== RAW FITBIT RESPONSE ===")
            if fitbit_data.get("heart_rate"):
                logger.info(f"Heart Rate Response: {fitbit_data['heart_rate']}")
            if fitbit_data.get("spo2"):
                logger.info(f"SpO2 Response: {fitbit_data['spo2']}")
            if fitbit_data.get("body_weight"):
                logger.info(f"Weight Response: {fitbit_data['body_weight']}")
            if fitbit_data.get("activity_summary"):
                logger.info(f"Activity Summary Response: {fitbit_data['activity_summary']}")
            if fitbit_data.get("calories_timeseries"):
                logger.info(f"Calories Timeseries Response: {fitbit_data['calories_timeseries']}")
            logger.info(f"=== END RAW FITBIT RESPONSE ===")
            
            # Map to FHIR Observations
            all_observations = []
            
            # Get user's timezone for observations
            user_timezone = user.timezone or "UTC"
            
            # Heart rate
            if fitbit_data.get("heart_rate"):
                hr_obs = fhir_mapper.map_fitbit_heart_rate(
                    patient_id=user.fhir_patient_id,
                    fitbit_data=fitbit_data["heart_rate"],
                    last_sync_datetime=last_sync_at,
                    user_timezone=user_timezone
                )
                all_observations.extend(hr_obs)
                logger.debug(f"Mapped {len(hr_obs)} heart rate observations")
            
            # SpO2
            if fitbit_data.get("spo2"):
                spo2_obs = fhir_mapper.map_fitbit_spo2(
                    patient_id=user.fhir_patient_id,
                    fitbit_data=fitbit_data["spo2"],
                    last_sync_datetime=last_sync_at,
                    user_timezone=user_timezone
                )
                all_observations.extend(spo2_obs)
                logger.debug(f"Mapped {len(spo2_obs)} SpO2 observations")
            
            # Weight
            if fitbit_data.get("body_weight"):
                weight_obs = fhir_mapper.map_fitbit_weight(
                    patient_id=user.fhir_patient_id,
                    fitbit_data=fitbit_data["body_weight"],
                    last_sync_datetime=last_sync_at,
                    user_timezone=user_timezone
                )
                all_observations.extend(weight_obs)
                logger.debug(f"Mapped {len(weight_obs)} weight observations")
            
            # Calories timeseries
            if fitbit_data.get("calories_timeseries"):
                calories_obs = fhir_mapper.map_fitbit_calories_timeseries(
                    patient_id=user.fhir_patient_id,
                    fitbit_data=fitbit_data["calories_timeseries"],
                    last_sync_datetime=last_sync_at,
                    user_timezone=user_timezone
                )
                all_observations.extend(calories_obs)
                logger.debug(f"Mapped {len(calories_obs)} calories observations")
            
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
            
            # Update last sync timestamp (typically only once per sync run)
            if integration and update_last_sync:
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

        # Current date in UTC for consistent day calculations
        utc_now = datetime.now(pytz.timezone("UTC"))
        today_utc = utc_now.date()

        for integration in integrations:
            if integration.vendor != "fitbit":
                logger.warning(f"Unsupported vendor: {integration.vendor}")
                continue

            # If a specific date is requested, keep existing single-day behavior
            if date_str:
                result = await self.sync_fitbit_data(db, user, date_str)
                results["vendors"].append(result)
                continue

            last_sync_at = integration.last_sync_at

            # No previous sync: sync only for today using existing behavior
            if not last_sync_at:
                result = await self.sync_fitbit_data(db, user, None)
                results["vendors"].append(result)
                continue

            last_sync_date = last_sync_at.date()

            # If last sync was today (or later), just perform a single incremental sync for today
            if last_sync_date >= today_utc:
                result = await self.sync_fitbit_data(
                    db=db,
                    user=user,
                    date_str=today_utc.isoformat(),
                    last_sync_at_override=last_sync_at,
                    update_last_sync=True,
                )
                results["vendors"].append(result)
                continue

            # Multi-day catch-up: increment daily from the day after last_sync up to today
            start_date = last_sync_date + timedelta(days=1)
            end_date = today_utc

            logger.info(
                f"Performing multi-day sync for user {user_id}, vendor fitbit "
                f"from {start_date.isoformat()} to {end_date.isoformat()} (last_sync_at={last_sync_at})"
            )

            current_date = start_date
            while current_date <= end_date:
                is_last_day = current_date == end_date
                current_date_str = current_date.isoformat()

                result = await self.sync_fitbit_data(
                    db=db,
                    user=user,
                    date_str=current_date_str,
                    last_sync_at_override=last_sync_at,
                    update_last_sync=is_last_day,
                )

                # Explicitly record the date synced in the result
                result["date"] = current_date_str
                results["vendors"].append(result)

                current_date += timedelta(days=1)
        
        logger.info(f"\n RESULTS: {results} \n")

        return results


sync_service = SyncService()
