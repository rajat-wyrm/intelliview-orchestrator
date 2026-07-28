# HR Dashboard API Contracts

## 1. Get Candidates
**Method and URL:** `GET /api/candidates`
**Auth requirements:** Required (Bearer Token)

**Request:**
```http
GET /api/candidates?domain=Python&status=completed&page=1&limit=10
```
```json
{
  "name": "HR Name",
  "department": "Engineering"
}
```
## 2. Get HR Profile
**Method and URL:** `GET /api/hr/profile`
**Auth requirements:** Required (Bearer Token)

**Request:**
```http
GET /api/hr/profile
```
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
```json
{
  "reason": "Candidate requested reschedule"
}
```
```json
{
  "message": "Schedule cancelled successfully",
  "scheduleId": "98765",
  "status": "CANCELLED"
}
```
```http
GET /api/notifications/unread-count
```
## 5. Get Unread Notifications Count
**Method and URL:** `GET /api/notifications/unread-count`
**Auth requirements:** Required (Bearer Token)

**Request:**
```http
GET /api/notifications/unread-count
```
```json
{
  "unreadCount": 12
}
```

