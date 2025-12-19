# PHR Backend API

A production-ready FastAPI backend for Personal Health Records (PHR) with FHIR integration and wearable device support.

## Features

- **Authentication**: JWT-based auth with user registration and login
- **User Management**: Complete CRUD operations with role-based access control
- **FHIR Integration**: Seamless integration with HAPI FHIR server
- **Fitbit Integration**: OAuth-based health data sync from Fitbit devices 🆕
- **Vendor-Agnostic API**: Standardized health data endpoints
- **Background Sync**: Automated health data synchronization
- **Database**: SQLAlchemy with PostgreSQL/SQLite support
- **Security**: Password hashing, token encryption, OAuth 2.0
- **API Documentation**: Automatic OpenAPI/Swagger documentation

## Tech Stack

- **Python 3.8+**
- **FastAPI** - Modern web framework
- **SQLAlchemy** - ORM and database toolkit
- **PostgreSQL/SQLite** - Database options
- **JWT** - Authentication tokens
- **Bcrypt** - Password hashing
- **Fernet** - Token encryption
- **Pydantic** - Data validation
- **httpx** - Async HTTP client for FHIR and Fitbit communication
- **Alembic** - Database migrations

## 🆕 Fitbit Integration

The PHR backend now supports Fitbit integration using Google Account OAuth. See:

- **[Fitbit Quick Start Guide](docs/FITBIT_QUICKSTART.md)** - Get started in minutes
- **[Fitbit Integration Documentation](docs/FITBIT_INTEGRATION.md)** - Complete technical details
- **[Implementation Summary](docs/IMPLEMENTATION_SUMMARY.md)** - What was built

### Key Capabilities

- ✅ OAuth 2.0 with Google Account
- ✅ Automatic token refresh
- ✅ Heart rate, SpO2, weight, activity data
- ✅ FHIR Observation mapping (LOINC codes)
- ✅ Vendor-agnostic API for mobile apps
- ✅ Background data synchronization
- ✅ Encrypted token storage

## Project Structure

```
phr_backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app and configuration
│   ├── config.py            # Settings and configuration
│   ├── database.py          # Database connection and session
│   ├── models/              # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── vendor_integration.py    # 🆕 Vendor & OAuth models
│   ├── schemas/             # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── fhir.py
│   │   └── vendor.py        # 🆕 Vendor integration schemas
│   ├── auth/                # Authentication utilities
│   │   ├── __init__.py
│   │   └── auth.py
│   ├── services/            # Business logic services
│   │   ├── __init__.py
│   │   ├── user_service.py
│   │   ├── encryption.py              # 🆕 Token encryption
│   │   ├── vendor_integration_service.py  # 🆕
│   │   ├── oauth_token_service.py     # 🆕
│   │   ├── fitbit_service.py          # 🆕 Fitbit API client
│   │   ├── fhir_mapper.py             # 🆕 FHIR mapping
│   │   └── sync_service.py            # 🆕 Data sync
│   ├── routers/             # API route handlers
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── integrations.py  # 🆕 Vendor selection
│   │   ├── fitbit.py        # 🆕 Fitbit OAuth
│   │   └── health.py        # 🆕 Health observations
│   │   ├── users.py
│   │   └── fhir.py
│   └── fhir/                # FHIR client and utilities
│       ├── __init__.py
│       └── client.py
├── alembic/                 # Database migrations
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variables template
├── alembic.ini             # Alembic configuration
└── README.md              # This file
```

## Installation

### 1. Clone the repository
```bash
git clone <repository-url>
cd phr_backend
```

### 2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
```bash
cp .env.example .env
```

Edit `.env` file with your configuration:

```env
# Database Configuration
DATABASE_URL=sqlite:///./phr.db
# For PostgreSQL: DATABASE_URL=postgresql://username:password@localhost/phr_db

# JWT Configuration
SECRET_KEY=your-very-secure-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# FHIR Configuration
FHIR_BASE_URL=http://localhost:8080/fhir

# Admin Configuration
ADMIN_EMAIL=admin@phr.com
ADMIN_PASSWORD=secure_admin_password

# Environment
ENVIRONMENT=development
```

### 5. Database Setup

#### Option A: SQLite (Quick Start)
```bash
# Database will be created automatically on first run
```

#### Option B: PostgreSQL
```bash
# Create database
createdb phr_db

# Update DATABASE_URL in .env
DATABASE_URL=postgresql://username:password@localhost/phr_db
```

### 6. Run Database Migrations
```bash
# Initialize Alembic (if not already done)
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head
```

## Running the Application

### Development
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - User login
- `POST /auth/token` - OAuth2 compatible login
- `GET /auth/me` - Get current user info

### User Management
- `GET /users` - List all users (admin only)
- `GET /users/{id}` - Get user by ID
- `POST /users` - Create user (admin only)  
- `PUT /users/{id}` - Update user
- `DELETE /users/{id}` - Delete user (admin only)

### FHIR Integration
- `POST /fhir/Patient` - Create Patient resource
- `GET /fhir/Patient/{id}` - Get Patient resource
- `PUT /fhir/Patient/{id}` - Update Patient resource
- `POST /fhir/Observation` - Create Observation resource
- `GET /fhir/Observation` - Search Observations
- `GET /fhir/Observation/{id}` - Get Observation resource
- `GET /fhir/{resource_type}` - Generic FHIR resource search
- `POST /fhir/{resource_type}` - Generic FHIR resource creation
- `GET /fhir/{resource_type}/{id}` - Generic FHIR resource retrieval

## Example API Usage

### 1. Register User
```bash
curl -X POST "http://localhost:8000/auth/register" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "password": "securepassword"
  }'
```

**Response:**
```json
{
  "id": 1,
  "name": "John Doe",
  "email": "john@example.com",
  "fhir_patient_id": "patient-123",
  "is_admin": false,
  "is_active": true,
  "created_at": "2024-01-01T10:00:00Z"
}
```

### 2. Login
```bash
curl -X POST "http://localhost:8000/auth/login" \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "john@example.com",
    "password": "securepassword"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 3. Get Current User
```bash
curl -X GET "http://localhost:8000/auth/me" \\
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### 4. Create FHIR Patient
```bash
curl -X POST "http://localhost:8000/fhir/Patient" \\
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \\
  -H "Content-Type: application/json" \\
  -d '{
    "resourceType": "Patient",
    "name": [{
      "use": "official",
      "family": "Doe",
      "given": ["John"]
    }],
    "gender": "male",
    "birthDate": "1990-01-01"
  }'
```

### 5. Create FHIR Observation
```bash
curl -X POST "http://localhost:8000/fhir/Observation" \\
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \\
  -H "Content-Type: application/json" \\
  -d '{
    "resourceType": "Observation",
    "status": "final",
    "category": [{
      "coding": [{
        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
        "code": "vital-signs"
      }]
    }],
    "code": {
      "coding": [{
        "system": "http://loinc.org",
        "code": "8310-5",
        "display": "Body temperature"
      }]
    },
    "subject": {
      "reference": "Patient/patient-123"
    },
    "effectiveDateTime": "2024-01-01T10:00:00Z",
    "valueQuantity": {
      "value": 36.5,
      "unit": "Cel",
      "system": "http://unitsofmeasure.org",
      "code": "Cel"
    }
  }'
```

### 6. Search Observations
```bash
curl -X GET "http://localhost:8000/fhir/Observation?patient=patient-123&category=vital-signs" \\
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Security Features

- **JWT Authentication**: Secure token-based authentication
- **Password Hashing**: Bcrypt for secure password storage  
- **Role-Based Access**: Admin and user roles with different permissions
- **FHIR Security**: Users can only access their own FHIR resources (unless admin)
- **CORS Support**: Configurable cross-origin request handling

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    email VARCHAR UNIQUE NOT NULL,
    password_hash VARCHAR NOT NULL,
    fhir_patient_id VARCHAR NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP NULL
);
```

## FHIR Integration

The backend acts as a proxy to a HAPI FHIR server. It:

1. **Does not store clinical data locally**
2. **Forwards all FHIR requests** to the configured FHIR server
3. **Links users to FHIR Patients** via `fhir_patient_id`
4. **Enforces security** - users can only access their own data
5. **Handles authentication** for FHIR API access

### Supported FHIR Resources
- **Patient** - Demographics and identity
- **Observation** - Clinical measurements and results
- **Condition** - Health conditions and diagnoses
- **MedicationRequest** - Prescriptions and medications
- **Procedure** - Medical procedures
- **And more...** (Generic endpoints support any FHIR resource)

## Development

### Code Style
- Follow PEP 8 guidelines
- Use type hints
- Document functions and classes

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Revert migration
alembic downgrade -1
```

### Testing
```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest
```

## Production Deployment

### Environment Variables
Set these in production:
```env
DATABASE_URL=postgresql://user:pass@host:5432/dbname
SECRET_KEY=very-secure-random-key-here
ENVIRONMENT=production
FHIR_BASE_URL=https://your-fhir-server.com/fhir
```

### Docker Deployment
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Security Considerations
1. **Use strong SECRET_KEY** in production
2. **Configure CORS properly** for your frontend domains
3. **Use HTTPS** for all communications
4. **Set up proper database permissions**
5. **Monitor and log API access**
6. **Regular security updates**

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Check DATABASE_URL in .env
   - Ensure database server is running
   - Verify credentials and database exists

2. **FHIR Server Connection Error**
   - Check FHIR_BASE_URL in .env
   - Ensure FHIR server is accessible
   - Verify network connectivity

3. **JWT Token Issues**
   - Check SECRET_KEY configuration
   - Verify token expiration settings
   - Ensure proper Authorization header format

## Support

For issues and questions:
1. Check this README
2. Review API documentation at `/docs`
3. Check application logs
4. Create an issue in the repository

## License

[Your License Here]