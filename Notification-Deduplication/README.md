# Notification Deduplication

## Problem Statement

Duplicate notifications can occur due to repeated notification requests (retries) in distributed systems. The objective of this project is to prevent users from receiving the same notification multiple times by implementing an idempotency-key mechanism.

The application generates a unique SHA-256 idempotency key using the combination of **Event Name**, **User ID**, and **Timestamp**. Before sending a notification, it checks whether the generated key already exists. If the key is found, the notification is skipped; otherwise, the notification is sent and recorded.

---

## Features

- Generates SHA-256 idempotency keys.
- Prevents duplicate notifications.
- Checks for existing notifications before sending.
- Returns JSON-formatted responses.
- Basic input validation for Event Name and User ID.
- Simple and lightweight Python implementation.

---

## Project Structure

```
Notification-Deduplication/
│
├── notification.py
├── deduplication.py
├── storage.py
├── requirements.txt
├── sample_output.txt
└── README.md
```

---

## Workflow

```
Notification Request
        │
        ▼
Generate SHA-256 Idempotency Key
        │
        ▼
Check Existing Notification
        │
   ┌────┴────┐
   │         │
Exists     Not Exists
   │         │
Skip      Send Notification
   │         │
   └────┬────┘
        ▼
Return JSON Response
```

---

## Installation Guide

### 1. Clone the Repository

```bash
git clone https://github.com/bhavana071/Notification-Deduplication.git
```

### 2. Navigate to the Project Folder

```bash
cd Notification-Deduplication
```

### 3. Run the Application

```bash
python notification.py
```

### Requirements

- Python 3.x
- No external libraries are required.

---

## Sample Output

### First Notification

```json
{
    "idempotency_key": "sha256:c984012ec55523e36c9a0a67db49a3f85a826d3eeb286d91871955c2c89e8530",
    "status": "sent",
    "sent_at": "2026-06-18T10:00:00"
}
```

### Duplicate Notification

```json
{
    "idempotency_key": "sha256:c984012ec55523e36c9a0a67db49a3f85a826d3eeb286d91871955c2c89e8530",
    "status": "skipped_duplicate",
    "original_sent_at": "2026-06-18T10:00:00"
}
```

---

## Manual Functional Testing

The application was tested manually by executing different notification scenarios and verifying the generated JSON responses.

### Test Case 1

**Input**

- Event: Interview
- User ID: 101
- Timestamp: 2026-06-18T10:00:00

**Output**

```
Status: sent
```

---

### Test Case 2

**Input**

- Event: Interview
- User ID: 101
- Timestamp: 2026-06-18T10:00:00

**Output**

```
Status: skipped_duplicate
```

---

### Test Case 3

**Input**

- Event: Interview
- User ID: 102
- Timestamp: 2026-06-18T10:00:00

**Output**

```
Status: sent
```

---

### Test Case 4

**Input**

- Event: Question Engine
- User ID: 102
- Timestamp: 2026-06-18T10:00:00

**Output**

```
Status: sent
```

### Test Case 5

**Input**

- Empty Event Name

**Output**


Error: Event Name cannot be empty.




### Test Case 6

**Input**

- Empty User ID

**Output**

```
Error: User ID cannot be empty.
```

---

## Challenges

|  Challenge |  Solution |
|-----------|----------|
| Choosing a unique identifier for each notification | Combined Event Name, User ID, and Timestamp to generate a SHA-256 idempotency key. |
| Detecting duplicate requests | Compared the generated idempotency key with previously stored keys before sending notifications. |
| Returning consistent responses | Implemented structured JSON responses for both successful and duplicate notification requests. |



## Performance Observation

During manual testing, SHA-256 key generation and duplicate lookup completed immediately for the tested notification scenarios. Since the project stores notification keys in memory, duplicate checking was performed efficiently for the sample dataset.



## Limitations

- Notification keys are stored only in memory during program execution.
- Restarting the application clears previously stored notification keys.
- Changing the timestamp generates a different idempotency key, causing the notification to be treated as a new request.
- The project uses manual functional testing and does not include an automated testing framework.


## Repository

GitHub Repository:

https://github.com/bhavana071/Notification-Deduplication


## Conclusion

This project successfully implements a Notification Deduplication mechanism using SHA-256 idempotency keys. By generating a unique key from the event name, user ID, and timestamp, the application verifies each notification request before sending it. Duplicate requests are identified and skipped, while new notifications are processed successfully.

The project demonstrates the implementation of idempotency-key logic, duplicate detection, JSON response generation, and basic input validation. Manual functional testing confirmed that the application behaves correctly for both unique and duplicate notification requests.