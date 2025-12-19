# FHIR Condition (Symptom) API Examples

## Overview
The backend now supports full CRUD operations for FHIR Condition resources, specifically designed for symptom tracking in PHR applications.

## Authentication
All endpoints require JWT authentication:
```
Authorization: Bearer <your-jwt-token>
```

## Endpoints

### 1. Create Condition (Symptom)
```http
POST /fhir/Condition
Content-Type: application/json
Authorization: Bearer <jwt-token>

{
  "code": {
    "coding": [
      {
        "system": "http://snomed.info/sct",
        "code": "84229001",
        "display": "Fatigue"
      }
    ],
    "text": "Fatigue"
  },
  "clinicalStatus": {
    "coding": [
      {
        "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
        "code": "active",
        "display": "Active"
      }
    ]
  },
  "category": [
    {
      "coding": [
        {
          "system": "http://terminology.hl7.org/CodeSystem/condition-category",
          "code": "problem-list-item",
          "display": "Problem List Item"
        }
      ]
    }
  ],
  "severity": {
    "coding": [
      {
        "system": "http://snomed.info/sct",
        "code": "255604002",
        "display": "Mild"
      }
    ]
  },
  "subject": {
    "reference": "Patient/123"
  },
  "onsetDateTime": "2023-12-01T10:30:00Z",
  "recordedDate": "2023-12-02T14:15:00Z"
}
```

### 2. Get All Conditions
```http
GET /fhir/Condition
Authorization: Bearer <jwt-token>
```

### 3. Get Conditions with Filters
```http
GET /fhir/Condition?patient=123&clinical-status=active&_count=10
Authorization: Bearer <jwt-token>
```

### 4. Get Specific Condition
```http
GET /fhir/Condition/{condition-id}
Authorization: Bearer <jwt-token>
```

### 5. Update Condition
```http
PUT /fhir/Condition/{condition-id}
Content-Type: application/json
Authorization: Bearer <jwt-token>

{
  "resourceType": "Condition",
  "id": "{condition-id}",
  "code": {
    "coding": [
      {
        "system": "http://snomed.info/sct",
        "code": "84229001",
        "display": "Fatigue"
      }
    ]
  },
  "clinicalStatus": {
    "coding": [
      {
        "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
        "code": "resolved",
        "display": "Resolved"
      }
    ]
  },
  "severity": {
    "coding": [
      {
        "system": "http://snomed.info/sct",
        "code": "6736007",
        "display": "Moderate"
      }
    ]
  }
}
```

### 6. Delete Condition
```http
DELETE /fhir/Condition/{condition-id}
Authorization: Bearer <jwt-token>
```

## Common SNOMED Codes for Symptoms

### Severity Codes:
- **Mild**: 255604002
- **Moderate**: 6736007  
- **Severe**: 24484000

### Common Symptom Codes:
- **Fatigue**: 84229001
- **Headache**: 25064002
- **Nausea**: 422587007
- **Fever**: 386661006
- **Cough**: 49727002
- **Shortness of breath**: 267036007
- **Chest pain**: 29857009
- **Abdominal pain**: 21522001

### Clinical Status Codes:
- **active**: Currently present
- **recurrence**: Returned after resolution
- **relapse**: Returned after remission
- **inactive**: Not currently present
- **remission**: Temporarily absent
- **resolved**: Permanently absent
- **unknown**: Status unclear

## Query Parameters

### Available Filters:
- `patient`: Filter by patient ID
- `category`: Filter by condition category
- `code`: Filter by condition code (SNOMED)
- `clinical-status`: Filter by clinical status
- `severity`: Filter by severity level
- `onset-date`: Filter by onset date range (e.g., `ge2023-01-01`)
- `recorded-date`: Filter by recorded date range
- `_count`: Limit number of results

### Date Range Examples:
- `onset-date=ge2023-01-01` - Greater than or equal to Jan 1, 2023
- `onset-date=le2023-12-31` - Less than or equal to Dec 31, 2023
- `onset-date=ge2023-01-01&onset-date=le2023-12-31` - Date range

## Response Format
All responses follow FHIR R4 standard format:

```json
{
  "resourceType": "Condition",
  "id": "condition-123",
  "meta": {
    "versionId": "1",
    "lastUpdated": "2023-12-02T14:15:30Z"
  },
  "clinicalStatus": {
    "coding": [
      {
        "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
        "code": "active",
        "display": "Active"
      }
    ]
  },
  "category": [
    {
      "coding": [
        {
          "system": "http://terminology.hl7.org/CodeSystem/condition-category",
          "code": "problem-list-item",
          "display": "Problem List Item"
        }
      ]
    }
  ],
  "severity": {
    "coding": [
      {
        "system": "http://snomed.info/sct",
        "code": "255604002",
        "display": "Mild"
      }
    ]
  },
  "code": {
    "coding": [
      {
        "system": "http://snomed.info/sct",
        "code": "84229001",
        "display": "Fatigue"
      }
    ],
    "text": "Fatigue"
  },
  "subject": {
    "reference": "Patient/123"
  },
  "onsetDateTime": "2023-12-01T10:30:00Z",
  "recordedDate": "2023-12-02T14:15:00Z"
}
```

## Error Handling
- **401**: Unauthorized (invalid/missing JWT token)
- **403**: Forbidden (accessing other user's conditions)
- **404**: Condition not found
- **500**: FHIR server error or connection issue

## Security Notes
- Users can only access their own conditions (linked via fhir_patient_id)
- Admin users can access all conditions
- All operations require valid JWT authentication
- Patient reference is automatically set for non-admin users