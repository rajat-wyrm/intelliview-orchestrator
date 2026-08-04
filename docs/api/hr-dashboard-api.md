# HR Dashboard API Contracts

## Response Schema Validation

This API contract now uses response models and schema validation for the main endpoints.

### Validation rules
- All response fields must match the defined schema types.
- String fields should be strings.
- Numeric fields such as score and risk values should be numeric and within allowed ranges.
- Optional fields may be null.
- Lists should contain the correct item type.

### Example validation response
```json
{
  "status": "system running",
  "timestamp": "2026-08-04T12:00:00Z"
}
```

## 1. Get Candidates
**Method and URL:** `GET /api/candidates`
**Auth requirements:** Required (Bearer Token)

**Request:**
```http
GET /api/candidates?domain=Python&status=completed&page=1&limit=10
```

**Success response:**
```json
{
  "count": 1,
  "candidates": [
    {
      "candidate_id": "cand-001",
      "name": "HR Name",
      "email": "hr@company.com",
      "resume_text": "Experienced Python engineer",
      "skills": ["Python", "FastAPI"]
    }
  ]
}
```

## 2. Get HR Profile
**Method and URL:** `GET /api/hr/profile`
**Auth requirements:** Required (Bearer Token)

**Request:**
```http
GET /api/hr/profile
```

**Success response:**
```json
{
  "id": "hr-123",
  "name": "HR Name",
  "email": "hr@company.com",
  "department": "Engineering"
}
```

## 3. Update HR Profile
**Method and URL:** `PUT /api/hr/profile`
**Auth requirements:** Required (Bearer Token)

**Request body example:**
```json
{
  "name": "Updated HR Name",
  "department": "Human Resources"
}
```

**Success response:**
```json
{
  "message": "Profile updated successfully",
  "updatedProfile": {
    "id": "hr-123",
    "name": "Updated HR Name",
    "department": "Human Resources"
  }
}
```

## 4. Cancel Schedule
**Method and URL:** `POST /api/schedules/:id/cancel`
**Auth requirements:** Required (Bearer Token)

**Request params example:**
```http
POST /api/schedules/98765/cancel
```

**Success response:**
```json
{
  "message": "Schedule cancelled successfully",
  "scheduleId": "98765",
  "status": "CANCELLED"
}
```

## 5. Get Unread Notifications Count
**Method and URL:** `GET /api/notifications/unread-count`
**Auth requirements:** Required (Bearer Token)

**Request:**
```http
GET /api/notifications/unread-count
```

**Success response:**
```json
{
  "unreadCount": 12
}
```

