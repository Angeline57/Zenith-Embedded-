# Zenith Sleep 
### Night Wandering & Fall Detection System for Alzheimer’s Patients

<div align="center">
  <img src="zenith_sleep_logo_design.png" alt="Zenith Sleep Logo" width="600">
</div>

## Project Overview

Zenith Sleep is an Internet-of-Things (IoT) system designed to monitor
**night wandering and fall events** in Alzheimer’s patients.
The system combines embedded sensing, cloud communication, and a
web-based user interface to provide **real-time caregiver awareness**
and improve patient safety.

This repository contains the **complete system**, including:
- Embedded sensor acquisition and processing
- Backend communication and data storage
- Frontend user interface and marketing website


---

 ## System Architecture

```text
  ┌───────────────────────┐      ┌───────────────────────┐      ┌───────────────────────┐
  │     [ EDGE LAYER ]    │      │    [ CLOUD LAYER ]    │      │    [ LOGIC LAYER ]    │
  │    (Raspberry Pi)     │      │(Firebase Realtime DB) │      │   (Remote Backend)    │
  ├───────────────────────┤      ├───────────────────────┤      ├───────────────────────┤
  │    /raspberry_pi      │      │    /database_hub      │      │       /backend        │
  │                       │      │                       │      │                       │
  │ • Sensor Data (I2C)   │ PUT  │    ┌─────────────┐    │ GET  │ • OAuth2 Auth Session │
  │ • Fall Detection Logic├─────►│    │ latest.json │    ├─────►│ • Process Logic       │
  │ • HTTP Client         │      │    └─────────────┘    │      │ • Status Calculation  │
  └───────────────────────┘      └──────────┬────────────┘      └───────────┬───────────┘
                                            │                               │
                                            │            PATCH              │
                                            │◄──────────────────────────────┘
                                            │    (Updates 'on_person' key)
                                            │
                                            ▼
                                ┌───────────────────────┐
                                │  [ PRESENTATION ]     │
                                │      /frontend        │
                                ├───────────────────────┤
                                │ • Web Dashboard UI    │
                                │ • Live Alerts Display │
                                │ • JS Fetch (Polling)  │
                                └───────────────────────┘
```

## Repository Structure

Zenith Sleep/
├── embedded/ # Raspberry Pi sensor acquisition & processing
├── backend/ # Cloud communication & database logic
├── frontend/ # Web-based UI and marketing website
└── README.md # Main project documentation


---

## 🛡️ Security & Authentication 
This system implements a multi-tier security model; the /backend utilizes OAuth2 Service Accounts for server-side database integrity, while the /frontend dashboard uses Firebase Authentication to ensure that only authorized caregivers can access private patient telemetry. Component-specific security design and implementation details are documented in the corresponding README files for each subsystem.

---

## Technologies Used

- **Python** – Embedded processing and backend logic
- **Raspberry Pi** – Edge computing platform
- **HTTP** – Device-to-cloud communication
- **Firebase Realtime Database** – Cloud storage
- **HTML / CSS / JavaScript** – Frontend user interface

---

## How to Run the Project

### Frontend Only (No Backend Required)

1. Navigate to the `frontend/` directory
2. Open `index.html` in a web browser
3. Enable mock data mode in `script.js`

This mode is suitable for:
- UI testing
- Demonstrations
- Video recordings

---

## Coursework Context

This project was developed as part of **Embedded Systems Coursework 1**
at **Imperial College London**.

The system demonstrates:
- Embedded sensor interfacing
- IoT communication using HTTP
- Cloud-based data storage
- User interface design for real-world applications
- Consideration of usability and scalability

---

## Future Extensions

Possible future improvements include:
- Caregiver authentication and user accounts
- Mobile application support
- Multi-patient monitoring
- Long-term data analytics and trend detection

