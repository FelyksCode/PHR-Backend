# Fitbit Integration Quick Start Guide

## Prerequisites

1. Python 3.8+
2. Running HAPI FHIR server
3. Fitbit Developer Account
4. PostgreSQL or SQLite database

## Step 1: Setup Fitbit Developer Account

1. Go to https://dev.fitbit.com/
2. Sign in or create an account
3. Click "Register an App"
4. Fill in the application details:
   - **Application Name**: PHR Backend
   - **Description**: Personal Health Record Backend
   - **Application Website**: http://localhost:8000
   - **Organization**: Your Organization
   - **OAuth 2.0 Application Type**: **Server**
   - **Callback URL**: `http://localhost:8000/integrations/fitbit/callback`
   - **Default Access Type**: Read-Only
5. Select the following scopes:
   - ✅ Activity & Exercise
   - ✅ Heart Rate
   - ✅ Weight & Body Measurements  
   - ✅ Oxygen Saturation (SpO2)
   - ✅ Profile
6. Agree to terms and create application
7. Copy **OAuth 2.0 Client ID** and **Client Secret**

## Step 2: Install Dependencies

```bash
cd phr_backend
pip install -r requirements.txt
```

## Step 3: Configure Environment Variables

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Generate encryption key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

3. Edit `.env` file with your credentials:
```env
# Fitbit OAuth
FITBIT_CLIENT_ID=YOUR_CLIENT_ID_FROM_STEP_1
FITBIT_CLIENT_SECRET=YOUR_CLIENT_SECRET_FROM_STEP_1
FITBIT_REDIRECT_URI=http://localhost:8000/integrations/fitbit/callback

# Encryption Key
ENCRYPTION_KEY=YOUR_GENERATED_KEY_FROM_STEP_2

# Database (use PostgreSQL in production)
DATABASE_URL=sqlite:///./phr.db

# FHIR Server
FHIR_BASE_URL=http://localhost:8080/fhir
```

## Step 4: Start FHIR Server (if not running)

Using Docker:
```bash
docker run -p 8080:8080 hapiproject/hapi:latest
```

Wait for server to start (check http://localhost:8080)

## Step 5: Run Database Migration

```bash
# Auto-create tables (development)
# Tables will be created on first run

# OR use Alembic (recommended for production)
alembic revision --autogenerate -m "Add vendor integration tables"
alembic upgrade head
```

## Step 6: Start the Backend Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Server will start at http://localhost:8000

## Step 7: Test the Integration

### 7.1 Access API Documentation
Open http://localhost:8000/docs

### 7.2 Create Admin User (automatic on startup)
Default credentials:
- Email: admin@phr.com
- Password: admin123

### 7.3 Login and Get JWT Token

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@phr.com",
    "password": "admin123"
  }'
```

Save the `access_token` from response.

### 7.4 Create FHIR Patient Record

```bash
curl -X POST "http://localhost:8000/fhir/patients" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "gender": "male",
    "birth_date": "1990-01-01"
  }'
```

### 7.5 Select Fitbit as Vendor

```bash
curl -X POST "http://localhost:8000/integrations/vendors/select" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "vendor": "fitbit"
  }'
```

### 7.6 Authorize with Fitbit

Open in browser (replace with your token):
```
http://localhost:8000/integrations/fitbit/authorize
```

Add this header in your browser dev tools or use a tool like Postman:
```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

You'll be redirected to Fitbit login. Sign in with your Google Account and authorize.

### 7.7 Check Connection Status

```bash
curl -X GET "http://localhost:8000/integrations/fitbit/status" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 7.8 Sync Fitbit Data

```bash
curl -X POST "http://localhost:8000/health/sync/immediate" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 7.9 Get Health Observations

```bash
curl -X GET "http://localhost:8000/health/observations?page=1&page_size=20" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Step 8: Flutter Integration

### Add Dependencies to pubspec.yaml
```yaml
dependencies:
  http: ^1.1.0
  webview_flutter: ^4.4.0
  flutter_secure_storage: ^9.0.0
```

### Example Flutter Service

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;

class HealthService {
  final String baseUrl = 'http://localhost:8000';
  String? _jwtToken;
  
  // Login
  Future<void> login(String email, String password) async {
    final response = await http.post(
      Uri.parse('$baseUrl/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({'email': email, 'password': password}),
    );
    
    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      _jwtToken = data['access_token'];
    }
  }
  
  // Select Fitbit vendor
  Future<void> selectFitbitVendor() async {
    await http.post(
      Uri.parse('$baseUrl/integrations/vendors/select'),
      headers: {
        'Authorization': 'Bearer $_jwtToken',
        'Content-Type': 'application/json',
      },
      body: json.encode({'vendor': 'fitbit'}),
    );
  }
  
  // Get OAuth URL and open in webview
  String getFitbitOAuthUrl() {
    return '$baseUrl/integrations/fitbit/authorize';
  }
  
  // Sync health data
  Future<void> syncHealthData() async {
    await http.post(
      Uri.parse('$baseUrl/health/sync'),
      headers: {'Authorization': 'Bearer $_jwtToken'},
    );
  }
  
  // Get health observations
  Future<List<dynamic>> getHealthObservations() async {
    final response = await http.get(
      Uri.parse('$baseUrl/health/observations?page=1&page_size=20'),
      headers: {'Authorization': 'Bearer $_jwtToken'},
    );
    
    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      return data['observations'];
    }
    return [];
  }
}
```

## Troubleshooting

### Error: "Fitbit OAuth credentials not configured"
- Check that `FITBIT_CLIENT_ID` and `FITBIT_CLIENT_SECRET` are set in `.env`
- Restart the server after updating `.env`

### Error: "Invalid encryption key format"
- Ensure `ENCRYPTION_KEY` is a valid Fernet key
- Regenerate: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

### OAuth callback returns 400 error
- Verify `FITBIT_REDIRECT_URI` in `.env` matches exactly what's in Fitbit app settings
- Ensure URL is `http://localhost:8000/integrations/fitbit/callback` (no trailing slash)

### No health data syncing
- Ensure you have recent Fitbit data (wear your device)
- Check that FHIR server is running: http://localhost:8080
- Verify user has a FHIR patient ID: `GET /users/me`

### Token refresh fails
- Check Fitbit app is still active in your Fitbit account
- Re-authorize if needed: `GET /integrations/fitbit/authorize`

## Production Deployment

1. **Use PostgreSQL** instead of SQLite
2. **Enable HTTPS** for all endpoints
3. **Update callback URL** to production domain
4. **Rotate encryption keys** regularly
5. **Setup Redis** for OAuth state storage
6. **Configure Celery** for background tasks
7. **Add monitoring** (Sentry, DataDog, etc.)
8. **Setup backups** for database
9. **Use environment-specific configs**
10. **Implement rate limiting**

## Next Steps

- Read [FITBIT_INTEGRATION.md](FITBIT_INTEGRATION.md) for detailed documentation
- Check API documentation at http://localhost:8000/docs
- Review [api_examples.md](api_examples.md) for more examples
- Setup background sync schedule
- Add more health data vendors

## Support

For issues or questions:
- Check logs: `tail -f logs/app.log`
- API docs: http://localhost:8000/docs
- Fitbit Developer Forum: https://community.fitbit.com/
