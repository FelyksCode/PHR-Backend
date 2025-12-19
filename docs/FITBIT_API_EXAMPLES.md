# Fitbit Integration API Examples

Complete workflow examples for testing the Fitbit integration.

## Prerequisites

- Backend server running at `http://localhost:8000`
- HAPI FHIR server running at `http://localhost:8080`
- Valid Fitbit OAuth credentials configured

## Complete Workflow

### Step 1: User Registration

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "password": "SecurePass123!"
  }'
```

**Response:**
```json
{
  "id": 1,
  "name": "John Doe",
  "email": "john@example.com",
  "is_admin": false,
  "is_active": true,
  "fhir_patient_id": null
}
```

### Step 2: Login

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePass123!"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Save the token:**
```bash
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Step 3: Create FHIR Patient

```bash
curl -X POST "http://localhost:8000/fhir/patients" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "gender": "male",
    "birth_date": "1990-01-01"
  }'
```

**Response:**
```json
{
  "message": "Patient created successfully",
  "patient_id": "patient-123",
  "resource": {
    "resourceType": "Patient",
    "id": "patient-123",
    "name": [{"text": "John Doe"}]
  }
}
```

### Step 4: Select Fitbit as Vendor

```bash
curl -X POST "http://localhost:8000/integrations/vendors/select" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "vendor": "fitbit"
  }'
```

**Response:**
```json
{
  "message": "Successfully selected fitbit integration",
  "vendor": "fitbit",
  "integration_id": 1
}
```

### Step 5: List User's Vendor Integrations

```bash
curl -X GET "http://localhost:8000/integrations/vendors" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "integrations": [
    {
      "id": 1,
      "vendor": "fitbit",
      "is_active": true,
      "last_sync_at": null,
      "created_at": "2024-12-19T10:30:00Z"
    }
  ]
}
```

### Step 6: Initiate Fitbit OAuth (Browser)

Open this URL in a browser with the Authorization header:

```
http://localhost:8000/integrations/fitbit/authorize
```

**For testing with curl (will redirect):**
```bash
curl -X GET "http://localhost:8000/integrations/fitbit/authorize" \
  -H "Authorization: Bearer $TOKEN" \
  -L
```

This will redirect to Fitbit's OAuth page. After authorization, you'll be redirected back to the callback URL.

### Step 7: Check Fitbit Connection Status

```bash
curl -X GET "http://localhost:8000/integrations/fitbit/status" \
  -H "Authorization: Bearer $TOKEN"
```

**Response (connected):**
```json
{
  "connected": true,
  "vendor": "fitbit",
  "integration_id": 1,
  "last_sync": null,
  "token_expired": false
}
```

**Response (not connected):**
```json
{
  "connected": false,
  "message": "Fitbit not connected"
}
```

### Step 8: Sync Fitbit Data (Immediate)

```bash
curl -X POST "http://localhost:8000/health/sync/immediate" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "user_id": 1,
  "date": "2024-12-19",
  "vendors": [
    {
      "user_id": 1,
      "vendor": "fitbit",
      "date": "2024-12-19",
      "success": true,
      "observations_created": 8,
      "errors": []
    }
  ]
}
```

### Step 9: Sync Fitbit Data (Background)

```bash
curl -X POST "http://localhost:8000/health/sync" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "message": "Health data sync initiated",
  "user_id": 1,
  "date": "2024-12-19"
}
```

### Step 10: Get Health Observations (All)

```bash
curl -X GET "http://localhost:8000/health/observations?page=1&page_size=20" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "observations": [
    {
      "id": "obs-1",
      "code": "8867-4",
      "code_system": "http://loinc.org",
      "display": "Heart rate",
      "value": 72.0,
      "unit": "beats/min",
      "effective_datetime": "2024-12-19T10:30:00Z",
      "patient_id": "patient-123"
    },
    {
      "id": "obs-2",
      "code": "59408-5",
      "code_system": "http://loinc.org",
      "display": "Oxygen saturation",
      "value": 98.0,
      "unit": "%",
      "effective_datetime": "2024-12-19T10:30:00Z",
      "patient_id": "patient-123"
    }
  ],
  "total": 8,
  "page": 1,
  "page_size": 20,
  "has_more": false
}
```

### Step 11: Filter Observations by Type

**Heart rate only:**
```bash
curl -X GET "http://localhost:8000/health/observations?observation_type=heart_rate&page=1&page_size=10" \
  -H "Authorization: Bearer $TOKEN"
```

**SpO2 only:**
```bash
curl -X GET "http://localhost:8000/health/observations?observation_type=spo2&page=1&page_size=10" \
  -H "Authorization: Bearer $TOKEN"
```

**Body weight only:**
```bash
curl -X GET "http://localhost:8000/health/observations?observation_type=body_weight&page=1&page_size=10" \
  -H "Authorization: Bearer $TOKEN"
```

**Steps only:**
```bash
curl -X GET "http://localhost:8000/health/observations?observation_type=steps&page=1&page_size=10" \
  -H "Authorization: Bearer $TOKEN"
```

### Step 12: Filter Observations by Date Range

```bash
curl -X GET "http://localhost:8000/health/observations?date_from=2024-12-01&date_to=2024-12-19&page=1&page_size=20" \
  -H "Authorization: Bearer $TOKEN"
```

### Step 13: Deactivate Fitbit Integration

```bash
curl -X DELETE "http://localhost:8000/integrations/vendors/1" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "message": "Vendor integration deactivated successfully"
}
```

## Python Examples

### Using requests library

```python
import requests
from datetime import date

BASE_URL = "http://localhost:8000"

class PHRClient:
    def __init__(self, email, password):
        self.base_url = BASE_URL
        self.token = None
        self.login(email, password)
    
    def login(self, email, password):
        """Login and get JWT token"""
        response = requests.post(
            f"{self.base_url}/auth/login",
            json={"email": email, "password": password}
        )
        response.raise_for_status()
        self.token = response.json()["access_token"]
    
    def _headers(self):
        """Get authorization headers"""
        return {"Authorization": f"Bearer {self.token}"}
    
    def select_fitbit_vendor(self):
        """Select Fitbit as vendor"""
        response = requests.post(
            f"{self.base_url}/integrations/vendors/select",
            headers=self._headers(),
            json={"vendor": "fitbit"}
        )
        response.raise_for_status()
        return response.json()
    
    def get_fitbit_status(self):
        """Check Fitbit connection status"""
        response = requests.get(
            f"{self.base_url}/integrations/fitbit/status",
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()
    
    def sync_health_data(self, date_str=None):
        """Sync health data immediately"""
        params = {}
        if date_str:
            params["date_str"] = date_str
        
        response = requests.post(
            f"{self.base_url}/health/sync/immediate",
            headers=self._headers(),
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def get_health_observations(self, page=1, page_size=20, 
                                observation_type=None, 
                                date_from=None, date_to=None):
        """Get health observations"""
        params = {
            "page": page,
            "page_size": page_size
        }
        if observation_type:
            params["observation_type"] = observation_type
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        
        response = requests.get(
            f"{self.base_url}/health/observations",
            headers=self._headers(),
            params=params
        )
        response.raise_for_status()
        return response.json()

# Usage example
if __name__ == "__main__":
    # Initialize client
    client = PHRClient("john@example.com", "SecurePass123!")
    
    # Select Fitbit
    result = client.select_fitbit_vendor()
    print(f"Vendor selected: {result}")
    
    # Check status
    status = client.get_fitbit_status()
    print(f"Connection status: {status}")
    
    # Sync data
    sync_result = client.sync_health_data()
    print(f"Sync result: {sync_result}")
    
    # Get observations
    observations = client.get_health_observations(
        observation_type="heart_rate",
        page=1,
        page_size=10
    )
    print(f"Found {observations['total']} heart rate observations")
    for obs in observations['observations']:
        print(f"  - {obs['display']}: {obs['value']} {obs['unit']}")
```

## JavaScript/TypeScript Examples

```javascript
const BASE_URL = 'http://localhost:8000';

class PHRClient {
  constructor() {
    this.token = null;
  }

  async login(email, password) {
    const response = await fetch(`${BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    
    const data = await response.json();
    this.token = data.access_token;
    return data;
  }

  async selectFitbitVendor() {
    const response = await fetch(`${BASE_URL}/integrations/vendors/select`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ vendor: 'fitbit' })
    });
    
    return await response.json();
  }

  async getHealthObservations(options = {}) {
    const params = new URLSearchParams({
      page: options.page || 1,
      page_size: options.pageSize || 20,
      ...(options.observationType && { observation_type: options.observationType }),
      ...(options.dateFrom && { date_from: options.dateFrom }),
      ...(options.dateTo && { date_to: options.dateTo })
    });

    const response = await fetch(
      `${BASE_URL}/health/observations?${params}`,
      {
        headers: { 'Authorization': `Bearer ${this.token}` }
      }
    );
    
    return await response.json();
  }

  async syncHealthData(dateStr = null) {
    const url = dateStr 
      ? `${BASE_URL}/health/sync/immediate?date_str=${dateStr}`
      : `${BASE_URL}/health/sync/immediate`;
    
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${this.token}` }
    });
    
    return await response.json();
  }
}

// Usage
(async () => {
  const client = new PHRClient();
  
  // Login
  await client.login('john@example.com', 'SecurePass123!');
  
  // Select vendor
  const selection = await client.selectFitbitVendor();
  console.log('Vendor selected:', selection);
  
  // Sync data
  const syncResult = await client.syncHealthData();
  console.log('Sync result:', syncResult);
  
  // Get observations
  const observations = await client.getHealthObservations({
    observationType: 'heart_rate',
    page: 1,
    pageSize: 10
  });
  
  console.log(`Found ${observations.total} observations`);
})();
```

## Error Handling Examples

### Handle 401 Unauthorized
```bash
curl -X GET "http://localhost:8000/health/observations" \
  -H "Authorization: Bearer invalid_token"
```

**Response (401):**
```json
{
  "detail": "Could not validate credentials"
}
```

### Handle 404 Not Found
```bash
curl -X DELETE "http://localhost:8000/integrations/vendors/999" \
  -H "Authorization: Bearer $TOKEN"
```

**Response (404):**
```json
{
  "detail": "Vendor integration not found"
}
```

### Handle 400 Bad Request
```bash
curl -X POST "http://localhost:8000/integrations/vendors/select" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "vendor": "invalid_vendor"
  }'
```

**Response (422):**
```json
{
  "detail": [
    {
      "loc": ["body", "vendor"],
      "msg": "value is not a valid enumeration member",
      "type": "type_error.enum"
    }
  ]
}
```

## Testing Tips

1. **Use Postman or Insomnia** for easy testing
2. **Save the JWT token** as an environment variable
3. **Check FHIR server** for created observations: http://localhost:8080
4. **Use the test script**: `python test_fitbit_setup.py`
5. **Check logs** for debugging: `tail -f logs/app.log`
6. **Use API docs**: http://localhost:8000/docs for interactive testing

## Next Steps

- Try the Python or JavaScript client examples
- Build a simple web dashboard
- Integrate with your Flutter app
- Add more health data types
- Implement data visualization
