import httpx
import json
from typing import Dict, Any, Optional, List
from fastapi import HTTPException, status
from app.config import settings

class FHIRClient:
    def __init__(self):
        self.base_url = settings.fhir_base_url
        self.timeout = 30.0
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to FHIR server"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        headers = {
            "Content-Type": "application/fhir+json",
            "Accept": "application/fhir+json"
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers, params=params)
                elif method.upper() == "POST":
                    response = await client.post(url, headers=headers, json=data)
                elif method.upper() == "PUT":
                    response = await client.put(url, headers=headers, json=data)
                elif method.upper() == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    raise HTTPException(
                        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                        detail=f"Method {method} not supported"
                    )
                
                # Handle FHIR server responses
                if response.status_code == 200 or response.status_code == 201:
                    try:
                        return response.json()
                    except json.JSONDecodeError:
                        return {"message": "Success", "status_code": response.status_code}
                elif response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Resource not found in FHIR server"
                    )
                elif response.status_code >= 400:
                    try:
                        error_detail = response.json()
                    except:
                        error_detail = {"message": f"FHIR server error: {response.status_code}"}
                    
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"FHIR server error: {error_detail}"
                    )
                
                return response.json()
                
            except httpx.TimeoutException:
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail="FHIR server timeout"
                )
            except httpx.ConnectError:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Cannot connect to FHIR server"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"FHIR client error: {str(e)}"
                )
    
    async def create_patient(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new Patient resource"""
        return await self._make_request("POST", "Patient", patient_data)
    
    async def get_patient(self, patient_id: str) -> Dict[str, Any]:
        """Get Patient resource by ID"""
        return await self._make_request("GET", f"Patient/{patient_id}")
    
    async def update_patient(self, patient_id: str, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update Patient resource"""
        return await self._make_request("PUT", f"Patient/{patient_id}", patient_data)
    
    async def create_observation(self, observation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new Observation resource"""
        return await self._make_request("POST", "Observation", observation_data)
    
    async def get_observations(self, patient_id: Optional[str] = None, **params) -> Dict[str, Any]:
        """Get Observation resources with optional filtering"""
        query_params = {}
        if patient_id:
            query_params["patient"] = patient_id
        query_params.update(params)
        
        return await self._make_request("GET", "Observation", params=query_params)
    
    async def get_observation(self, observation_id: str) -> Dict[str, Any]:
        """Get Observation resource by ID"""
        return await self._make_request("GET", f"Observation/{observation_id}")
    
    async def search_resources(self, resource_type: str, **params) -> Dict[str, Any]:
        """Generic search for any FHIR resource type"""
        return await self._make_request("GET", resource_type, params=params)
    
    async def create_resource(self, resource_type: str, resource_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create any FHIR resource"""
        return await self._make_request("POST", resource_type, resource_data)
    
    async def get_resource(self, resource_type: str, resource_id: str) -> Dict[str, Any]:
        """Get any FHIR resource by type and ID"""
        return await self._make_request("GET", f"{resource_type}/{resource_id}")

# Global FHIR client instance
fhir_client = FHIRClient()