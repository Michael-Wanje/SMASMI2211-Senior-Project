SMASMI2211 – Senior Project

Project Title: Visitor Management System for Apartments & Gated Communities.

This project is a mobile-first, digital visitor management solution designed for apartments and gated communities. It replaces traditional logbooks with a secure, real-time communication platform that connects visitors, residents, and security personnel.



## Project Structure

```
FinalSeniorProject/
├── visitor_management_system/          # Flutter Frontend
│   ├── lib/
│   ├── android/
│   ├── ios/
│   ├── pubspec.yaml
│   └── ...
└── visitor_management_backend/         # Django Backend
    ├── visitor_management/
    ├── authentication/
    ├── manage.py
    ├── requirements.txt
    └── ...
```

## Setup Instructions

### Backend (Django)
1. Navigate to the backend directory:
   ```bash
   cd visitor_management_backend
   ```

2. Create and activate virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run migrations:
   ```bash
   python manage.py migrate
   ```

5. Start the server:
   ```bash
   python manage.py runserver
   ```

### Frontend (Flutter)
1. Navigate to the frontend directory:
   ```bash
   cd visitor_management_system
   ```

2. Get dependencies:
   ```bash
   flutter pub get
   ```

3. Run the app:
   ```bash
   flutter run
   ```

## Features
- User Authentication
- Visitor Registration
- Real-time Notifications
- Admin Dashboard
- Security Management

## Technologies Used
- **Frontend**: Flutter, Dart
- **Backend**: Django, Python
- **Database**: PostgreSQL
- **Authentication**: JWT


## 🔍 Project Overview

The system aims to:
- Improve security by accurately tracking all visitor entries and exits
- Allow residents to pre-approve or deny visitors via a mobile app
- Maintain digital visitor records for future reference
- Alert security personnel of blacklisted or unauthorized visitors



## 🛠️ Tech Stack

| Component | Technology |
|----------|-------------|
| **Frontend** | Flutter (Android) |
| **Backend** | Django (Python) |
| **Database** | PostgreSQL |
| **Email Notifications** | Gmail SMTP |



## 👨‍💻 Author

**Masaba Michael Wanje**  
`SMASMI2211`  
**Supervisor**: Jefferson Mwatati

---

## 🔒 Disclaimer

This is a university final-year project for demonstration and learning purposes only.
