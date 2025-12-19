# Fitbit Integration - PHR Backend

## Overview

This implementation adds Fitbit Web API integration to the PHR backend using Google Account OAuth. The integration is entirely server-side, with the Flutter mobile app consuming vendor-agnostic FHIR-based health data APIs.

## Architecture

```
Flutter App → PHR Backend → Fitbit API → HAPI FHIR Server
              ↓
         (OAuth, Token Management, Data Normalization)
```

### Key Components

1. **Vendor Selection** - User selects Fitbit as their health data provider
2. **OAuth Flow** - Secure authorization using Google Account via Fitbit OAuth 2.0
3. **Token Management** - Encrypted storage and automatic refresh of OAuth tokens
4. **Data Fetching** - Retrieval of heart rate, SpO2, weight, and activity data
5. **FHIR Mapping** - Normalization to FHIR Observation resources
6. **Background Sync** - Periodic data synchronization
7. **Vendor-Agnostic API** - Flutter consumes standard FHIR observations

## Environment Variables

Add these to your `.env` file:

```env
# Fitbit OAuth Configuration
FITBIT_CLIENT_ID=your_fitbit_client_id_here
FITBIT_CLIENT_SECRET=your_fitbit_client_secret_here
FITBIT_REDIRECT_URI=http://localhost:8000/integrations/fitbit/callback

# Encryption Key for OAuth Tokens (32-byte Fernet key)
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=your_encryption_key_here
```

## Database Migration

Run Alembic migration to create new tables:

```bash
# Generate migration
alembic revision --autogenerate -m "Add vendor integration tables"

# Apply migration
alembic upgrade head
```

Or let SQLAlchemy auto-create tables on startup (development only).

## API Endpoints

### 1. Vendor Selection

**Select Fitbit as vendor:**
```http
POST /integrations/vendors/select
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "vendor": "fitbit"
}
```

**Response:**
```json
{
  "message": "Successfully selected fitbit integration",
  "vendor": "fitbit",
  "integration_id": 1
}
```

### 2. Fitbit OAuth Flow

**Initiate authorization:**
```http
GET /integrations/fitbit/authorize
Authorization: Bearer <jwt_token>
```

This redirects to Fitbit's OAuth page. User logs in with Google Account and grants permissions.

**OAuth callback** (handled automatically):
```http
GET /integrations/fitbit/callback?code=<auth_code>&state=<state_token>
```

**Check connection status:**
```http
GET /integrations/fitbit/status
Authorization: Bearer <jwt_token>
```

### 3. Sync Health Data

**Background sync:**
```http
POST /health/sync
Authorization: Bearer <jwt_token>
```

**Immediate sync with results:**
```http
POST /health/sync/immediate?date_str=2024-12-19
Authorization: Bearer <jwt_token>
```

### 4. Get Health Observations (Vendor-Agnostic)

**Fetch all observations:**
```http
GET /health/observations?page=1&page_size=20
Authorization: Bearer <jwt_token>
```

**Filter by type:**
```http
GET /health/observations?observation_type=heart_rate&page=1&page_size=20
Authorization: Bearer <jwt_token>
```

**Filter by date range:**
```http
GET /health/observations?date_from=2024-12-01&date_to=2024-12-19
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "observations": [
    {
      "id": "123",
      "code": "8867-4",
      "code_system": "http://loinc.org",
      "display": "Heart rate",
      "value": 72.0,
      "unit": "beats/min",
      "effective_datetime": "2024-12-19T10:30:00",
      "patient_id": "patient-123"
    }
  ],
  "total": 50,
  "page": 1,
  "page_size": 20,
  "has_more": true
}
```

## FHIR Observation Mappings

| Fitbit Data | LOINC Code | Display Name | Unit |
|-------------|------------|--------------|------|
| Heart Rate | 8867-4 | Heart rate | beats/min |
| SpO2 | 59408-5 | Oxygen saturation | % |
| Body Weight | 29463-7 | Body weight | kg |
| Steps | 41950-7 | Number of steps | steps |
| Calories | 41981-2 | Calories burned | kcal |
| Distance | 41953-1 | Distance walked | km |

## Security Features

### Token Encryption
- OAuth tokens are encrypted at rest using Fernet (symmetric encryption)
- Encryption key must be 32 bytes (base64-encoded)
- Tokens are decrypted only when needed for API calls

### CSRF Protection
- State parameter used in OAuth flow
- State tokens stored temporarily and validated on callback

### JWT Authentication
- All endpoints require JWT authentication
- Users can only access their own health data

## Fitbit OAuth Scopes

The integration requests these scopes:
- `activity` - Steps, distance, calories
- `heartrate` - Heart rate data
- `oxygen_saturation` - SpO2 data
- `weight` - Body weight data
- `profile` - User profile information

## Error Handling

### Common Errors

**Missing Fitbit credentials:**
```json
{
  "detail": "Fitbit OAuth credentials not configured"
}
```

**Token expired (handled automatically):**
- Access tokens are automatically refreshed using refresh token
- No user intervention required

**Rate limiting:**
```json
{
  "detail": "Rate limit exceeded. Please try again later."
}
```

**No FHIR patient ID:**
```json
{
  "detail": "User does not have a FHIR patient record"
}
```

## Background Sync

### Manual Sync
Use the `/health/sync` endpoint to trigger background synchronization.

### Scheduled Sync (Optional)
For periodic syncing, you can use:

1. **Celery** - Add a periodic task:
```python
from celery import Celery
from celery.schedules import crontab

@app.task
def sync_all_users():
    # Sync logic here
    pass

app.conf.beat_schedule = {
    'sync-every-hour': {
        'task': 'tasks.sync_all_users',
        'schedule': crontab(minute=0),
    },
}
```

2. **FastAPI Background Tasks** - For simpler setups (used in this implementation)

## Flutter Integration

### Flow

1. **User Login** - Authenticate with PHR backend (JWT)
2. **Select Vendor** - POST to `/integrations/vendors/select`
3. **OAuth Authorization** - Open webview to `/integrations/fitbit/authorize`
4. **Fetch Data** - GET from `/health/observations` (vendor-agnostic)
5. **Periodic Sync** - POST to `/health/sync` daily

### Example Flutter Code

```dart
// Select Fitbit vendor
Future<void> selectFitbitVendor() async {
  final response = await http.post(
    Uri.parse('$baseUrl/integrations/vendors/select'),
    headers: {'Authorization': 'Bearer $jwtToken'},
    body: json.encode({'vendor': 'fitbit'}),
  );
}

// Open OAuth in webview
Future<void> authorizeWithFitbit() async {
  final url = '$baseUrl/integrations/fitbit/authorize';
  // Launch webview
  await launch(url);
}

// Get health observations
Future<List<Observation>> getHealthObservations() async {
  final response = await http.get(
    Uri.parse('$baseUrl/health/observations?page=1&page_size=20'),
    headers: {'Authorization': 'Bearer $jwtToken'},
  );
  
  final data = json.decode(response.body);
  return (data['observations'] as List)
      .map((obs) => Observation.fromJson(obs))
      .toList();
}
```

## Testing

### Local Testing

1. **Start FHIR server** (HAPI FHIR):
```bash
docker run -p 8080:8080 hapiproject/hapi:latest
```

2. **Set environment variables** in `.env`

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Run migrations**:
```bash
alembic upgrade head
```

5. **Start server**:
```bash
uvicorn app.main:app --reload
```

6. **Test endpoints** using the API documentation at `http://localhost:8000/docs`

### Manual OAuth Testing

1. Register at https://dev.fitbit.com/
2. Create an application
3. Set OAuth 2.0 Application Type to "Server"
4. Add callback URL: `http://localhost:8000/integrations/fitbit/callback`
5. Copy Client ID and Client Secret to `.env`

## Production Considerations

1. **Use Redis** for OAuth state storage instead of in-memory dict
2. **Enable Celery** for production-grade background task processing
3. **Configure proper CORS** settings in `main.py`
4. **Use HTTPS** for all OAuth callbacks
5. **Rotate encryption keys** periodically
6. **Monitor API rate limits** from Fitbit
7. **Implement retry logic** for FHIR server errors
8. **Add logging and monitoring** (e.g., Sentry, CloudWatch)

## Troubleshooting

### Tokens not refreshing
- Check that refresh token is stored
- Verify encryption key hasn't changed
- Check Fitbit API credentials

### No data syncing
- Verify user has FHIR patient ID
- Check FHIR server is running
- Review logs for API errors
- Ensure OAuth scopes include required permissions

### OAuth callback fails
- Verify redirect URI matches Fitbit app settings exactly
- Check state token is valid
- Ensure HTTPS in production

## Next Steps

1. **Add more vendors** (Apple Health, Google Fit, etc.)
2. **Implement webhook notifications** from Fitbit
3. **Add data caching** layer
4. **Create admin dashboard** for monitoring sync jobs
5. **Add notification system** for sync failures

## License

[Your License Here]

## Support

For issues or questions, contact [Your Support Email]
