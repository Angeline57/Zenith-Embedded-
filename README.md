# 🛡️ SafeSleep  
### Night Wandering & Fall Detection System for Alzheimer’s Patients

## Project Overview

SafeSleep is an Internet-of-Things (IoT) system designed to monitor
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
┌────────────────────┐
│ Sensors │
│ • 9DOF IMU │
│ • Time-of-Flight │
└─────────┬──────────┘
│
▼
┌────────────────────┐
│ Raspberry Pi │
│ Embedded Python │
│ - Sensor fusion │
│ - Fall detection │
│ - Wandering logic │
└─────────┬──────────┘
│
▼
┌────────────────────┐
│ Cloud Backend │
│ Firebase / MQTT │
│ - Data storage │
│ - Remote access │
└─────────┬──────────┘
│
▼
┌────────────────────┐
│ Frontend Web UI │
│ Marketing + Dashboard│
│ - Status display │
│ - Alerts │
└────────────────────┘

---

## Repository Structure

SafeSleep/
├── embedded/ # Raspberry Pi sensor acquisition & processing
├── backend/ # Cloud communication & database logic
├── frontend/ # Web-based UI and marketing website
├── docs/ # Coursework documentation and diagrams
└── README.md # Main project documentation


---

## Subsystems Description

### Embedded System (Raspberry Pi)

- Interfaces with:
  - 9DOF inertial measurement unit (IMU)
  - Time-of-Flight distance sensor
- Performs:
  - Motion analysis
  - Fall detection
  - Bed exit and wandering detection
- Outputs **processed, high-level states**
  rather than raw sensor data

---

### Backend & Cloud Communication

- Uses:
  - MQTT for message passing
  - HTTP (REST) for database interaction
- Stores processed sensor data in a cloud database
- Enables remote monitoring and scalability

The backend abstracts the embedded system from the frontend,
allowing independent development of both components.

---

### Frontend (Web Interface)

Located in the `frontend/` directory.

The frontend is a **single-page web application** that serves two roles:
1. **Marketing website** explaining the product concept
2. **Live monitoring dashboard** for caregivers

Key features:
- Displays patient state (sleeping, wandering, fall detected)
- Clear alert messages for critical events
- Designed for clarity and non-technical users

Mock data mode is supported to allow development before backend
integration.

---

## Technologies Used

- **Python** – Embedded processing and backend logic
- **Raspberry Pi** – Edge computing platform
- **MQTT / HTTP** – Device-to-cloud communication
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
- IoT communication using MQTT and HTTP
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

