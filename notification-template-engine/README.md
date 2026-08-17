# Multi-Language Notification Template Engine

## Overview

This project implements a multilingual notification template engine in Python. Notifications are generated according to each user's preferred language (locale). The system loads language-specific templates, replaces placeholders dynamically, and generates personalized notifications.

The application currently supports:

- English (en)
- Hindi (hi)
- Telugu (te)

It also supports multiple notification events such as interview scheduling, reminders, cancellations, and completion notifications.

---

# Features

- Multi-language notification templates
- Locale-based template loading
- English fallback for unsupported locales
- Dynamic placeholder rendering
- Multiple notification events
- Input validation
- Exception handling
- Template validation
- Logging support
- Unicode support
- Unit testing

---

# Supported Notification Events

- interview_scheduled
- interview_reminder
- interview_cancelled
- interview_completed

---

# Supported Placeholders

Templates can contain the following placeholders:

- {{name}}
- {{date}}
- {{time}}

These placeholders are replaced automatically while generating notifications.

---

# Project Structure

```
notification-project/

│
├── templates/
│   ├── en/
│   │   ├── interview_scheduled.txt
│   │   ├── interview_reminder.txt
│   │   ├── interview_cancelled.txt
│   │   └── interview_completed.txt
│   │
│   ├── hi/
│   │   ├── interview_scheduled.txt
│   │   ├── interview_reminder.txt
│   │   ├── interview_cancelled.txt
│   │   └── interview_completed.txt
│   │
│   └── te/
│       ├── interview_scheduled.txt
│       ├── interview_reminder.txt
│       ├── interview_cancelled.txt
│       └── interview_completed.txt
│
├── users.py
├── template_loader.py
├── notification_service.py
├── main.py
├── test_notification.py
└── README.md
```

---

# Technologies Used

- Python 3
- Visual Studio Code
- OS Module
- Logging Module
- Regular Expressions (re)
- unittest
- Git
- GitHub

---

# Running the Project

Clone the repository

```
git clone <repository-url>
```

Move to the project directory

```
cd notification-project
```

Run the application

```
python main.py
```

Run unit tests

```
python -m unittest test_notification.py
```

---

# Error Handling

The project validates:

- Invalid user details
- Invalid email addresses
- Empty templates
- Missing template files
- Invalid placeholders
- Invalid notification events
- Missing notification data
- Unsupported locales

---

# Logging

The system records important events including:

- Template loading
- Locale fallback
- Notification generation
- File loading errors

---

# Future Enhancements

- Email notification integration
- SMS notification support
- Database integration
- Automatic language discovery
- Configurable language registry
- Jinja2 template engine support
- REST API integration

---

# Author

**Vaishnavi Jagdale**
