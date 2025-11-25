# PHR Backend API Example Requests

## Set base URL
BASE_URL=http://localhost:8000

## 1. Health Check
GET {{BASE_URL}}/health

### Response
```json
{
  "status": "healthy"
}
```

---

## 2. Register New User
POST {{BASE_URL}}/auth/register
Content-Type: application/json

{
  "name": "John Doe",
  "email": "john@example.com", 
  "password": "securepassword123"
}

### Response
```json
{
  "id": 1,
  "name": "John Doe",
  "email": "john@example.com",
  "fhir_patient_id": "12345",
  "is_admin": false,
  "is_active": true,
  "created_at": "2024-01-01T10:00:00Z"
}
```

---

## 3. Login User
POST {{BASE_URL}}/auth/login
Content-Type: application/json

{
  "email": "john@example.com",
  "password": "securepassword123"
}

### Response
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

## 4. Get Current User Info
GET {{BASE_URL}}/auth/me
Authorization: Bearer YOUR_ACCESS_TOKEN

### Response
```json
{
  "id": 1,
  "name": "John Doe", 
  "email": "john@example.com",
  "fhir_patient_id": "12345",
  "is_admin": false,
  "is_active": true,
  "created_at": "2024-01-01T10:00:00Z"
}
```

---

## 5. Create FHIR Patient
POST {{BASE_URL}}/fhir/Patient
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json

{
  "resourceType": "Patient",
  "name": [
    {
      "use": "official",
      "family": "Doe",
      "given": ["John"]
    }
  ],
  "telecom": [
    {
      "system": "email",
      "value": "john@example.com",
      "use": "home"
    }
  ],
  "gender": "male",
  "birthDate": "1990-01-01",
  "address": [
    {
      "use": "home",
      "type": "physical",
      "line": ["123 Main St"],
      "city": "Anytown",
      "postalCode": "12345",
      "country": "US"
    }
  ],
  "active": true
}

### Response
```json
{
  "resourceType": "Patient",
  "id": "12345",
  "meta": {
    "versionId": "1",
    "lastUpdated": "2024-01-01T10:00:00Z"
  },
  "name": [...],
  "telecom": [...],
  "gender": "male",
  "birthDate": "1990-01-01"
}
```

---

## 6. Get FHIR Patient
GET {{BASE_URL}}/fhir/Patient/12345
Authorization: Bearer YOUR_ACCESS_TOKEN

---

## 7. Create FHIR Observation (Vital Signs)
POST {{BASE_URL}}/fhir/Observation
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json

{
  "resourceType": "Observation",
  "status": "final",
  "category": [
    {
      "coding": [
        {
          "system": "http://terminology.hl7.org/CodeSystem/observation-category",
          "code": "vital-signs",
          "display": "Vital Signs"
        }
      ]
    }
  ],
  "code": {
    "coding": [
      {
        "system": "http://loinc.org",
        "code": "8310-5",
        "display": "Body temperature"
      }
    ]
  },
  "subject": {
    "reference": "Patient/12345"
  },
  "effectiveDateTime": "2024-01-01T10:00:00Z",
  "valueQuantity": {
    "value": 36.5,
    "unit": "Cel",
    "system": "http://unitsofmeasure.org",
    "code": "Cel"
  }
}

---

## 8. Create Blood Pressure Observation
POST {{BASE_URL}}/fhir/Observation
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json

{
  "resourceType": "Observation", 
  "status": "final",
  "category": [
    {
      "coding": [
        {
          "system": "http://terminology.hl7.org/CodeSystem/observation-category",
          "code": "vital-signs",
          "display": "Vital Signs"
        }
      ]
    }
  ],
  "code": {
    "coding": [
      {
        "system": "http://loinc.org",
        "code": "85354-9",
        "display": "Blood pressure panel with all children optional"
      }
    ]
  },
  "subject": {
    "reference": "Patient/12345"
  },
  "effectiveDateTime": "2024-01-01T10:00:00Z",
  "component": [
    {
      "code": {
        "coding": [
          {
            "system": "http://loinc.org",
            "code": "8480-6",
            "display": "Systolic blood pressure"
          }
        ]
      },
      "valueQuantity": {
        "value": 120,
        "unit": "mmHg",
        "system": "http://unitsofmeasure.org",
        "code": "mm[Hg]"
      }
    },
    {
      "code": {
        "coding": [
          {
            "system": "http://loinc.org",
            "code": "8462-4", 
            "display": "Diastolic blood pressure"
          }
        ]
      },
      "valueQuantity": {
        "value": 80,
        "unit": "mmHg",
        "system": "http://unitsofmeasure.org",
        "code": "mm[Hg]"
      }
    }
  ]
}

---

## 9. Search Observations for Patient
GET {{BASE_URL}}/fhir/Observation?patient=12345&category=vital-signs
Authorization: Bearer YOUR_ACCESS_TOKEN

---

## 10. Search Observations with Date Filter
GET {{BASE_URL}}/fhir/Observation?patient=12345&date=ge2024-01-01&date=le2024-12-31
Authorization: Bearer YOUR_ACCESS_TOKEN

---

## 11. Get Specific Observation
GET {{BASE_URL}}/fhir/Observation/obs-123
Authorization: Bearer YOUR_ACCESS_TOKEN

---

## 12. Admin - List All Users
GET {{BASE_URL}}/users
Authorization: Bearer ADMIN_ACCESS_TOKEN

---

## 13. Admin - Create User
POST {{BASE_URL}}/users
Authorization: Bearer ADMIN_ACCESS_TOKEN
Content-Type: application/json

{
  "name": "Jane Smith",
  "email": "jane@example.com",
  "password": "securepassword456"
}

---

## 14. Update User Profile
PUT {{BASE_URL}}/users/1
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json

{
  "name": "John Updated Doe"
}

---

## 15. Admin Login
POST {{BASE_URL}}/auth/login
Content-Type: application/json

{
  "email": "admin@phr.com",
  "password": "admin123"
}

---

## Notes:
1. Replace YOUR_ACCESS_TOKEN with actual token from login response
2. Replace ADMIN_ACCESS_TOKEN with admin token
3. Replace patient/observation IDs with actual values returned from FHIR server
4. Ensure FHIR server is running at configured URL (default: http://localhost:8080/fhir)
5. Default admin credentials are in .env file (admin@phr.com / admin123)