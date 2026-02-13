# Zenith Sleep 
### Night Wandering & Fall Detection System for Alzheimer’s Patients

<div align="center">
  <img src="zenith_sleep_logo_design.png" alt="Zenith Sleep Logo" width="600">
</div>

## Project Overview

Zenith Sleep is an Internet-of-Things (IoT) system designed to monitor **Sleepwalking and fall events** in patients. The system combines embedded sensing, cloud communication, and a web-based user interface to provide **real-time caregiver awareness** and improve patient safety.

This repository contains the **complete system**, including:
- Embedded sensor acquisition and processing
- Backend communication and data storage
- Frontend user interface and marketing website

This project was completed under the supervision of [Dr. Edward Stott](https://profiles.imperial.ac.uk/ed.stott) at Imperial College London, Department of Electrical and Electronic Engineering.

### Project Contributors:
- [Angeline Lin](https://github.com/Angeline57)
- [Hyojung Hwang](https://github.com/hh4023)
- [Krish Jindal](https://github.com/Alphablaze72)

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
```text

Zenith-Embedded-/
├── embedded/               # Raspberry Pi sensor acquisition & processing
├── backend/                # Cloud communication & database logic
│   ├── ML_device_worn.py   # ML device-worn detector (optional)
│   ├── train_device_worn.py# Train ML weights from fake data
│   └── fake_temp_data.csv  # Synthetic temperature dataset
├── frontend/               # Web UI (marketing + app)
│   ├── marketing/          # Marketing website + doctor/user dashboards
│   ├── app/                # App UI (login, dashboard, simulator, PWA)
│   └── README.md           # Frontend-specific notes
└── README.md               # Main project documentation

```
---

## Security & Authentication 
This system implements a multi-tier security model; the [backend](./backend) utilizes OAuth2 Service Accounts for server-side database integrity, while the [frontend](./frontend) dashboard uses Firebase Authentication to ensure that only authorized caregivers can access private patient telemetry. Component-specific security design and implementation details are documented in the corresponding README files for each subsystem.

---

## Technologies Used

- **Python** – Embedded processing and backend logic
- **Raspberry Pi** – Edge computing platform
- **HTTP** – Device-to-cloud communication
- **Firebase Realtime Database** – Cloud storage
- **HTML / CSS / JavaScript** – Frontend user interface

---

## Zenith Sleep App Features

- Live fall detection alerts (from Firebase `/latest.json`)
- Live sleepwalking detection status
- Device wear status (`device_on_person`)
- Device temperature display (`tmp_die_c`)
- Weekly and monthly sleepwalking counts
- Doctor notes synced between app and doctor dashboard
- “Last update” timestamp for live telemetry
- User and doctor dashboards on the marketing site
- App login screen + PWA support
- Simulator controls (separate page for demos)
- ML-based device-worn detection (backend-supported)

---

## How to Run the Project

### 1) Frontend (Marketing + App UI)

Open these directly in your web browser (GitHub Pages):

- Marketing site: `https://angeline57.github.io/Zenith-Embedded-/frontend/marketing/index.html`
- Marketing login: `https://angeline57.github.io/Zenith-Embedded-/frontend/marketing/login.html`
- Doctor dashboard: `https://angeline57.github.io/Zenith-Embedded-/frontend/marketing/doctor_dashboard.html`
- User dashboard: `https://angeline57.github.io/Zenith-Embedded-/frontend/marketing/user_dashboard.html`
- App login: `https://angeline57.github.io/Zenith-Embedded-/frontend/app/login.html`
- App dashboard: `https://angeline57.github.io/Zenith-Embedded-/frontend/app/app.html`
- Simulator (only to test app without hardware): `https://angeline57.github.io/Zenith-Embedded-/frontend/app/sim.html`

Notes:
- The app reads live data from Firebase `/latest.json`.
- Doctor notes and sleepwalking counts sync between app and doctor dashboard via `localStorage`
  (requires both pages to be served from the same origin).

### 2) Embedded (Raspberry Pi)

Run the sensor + detection pipeline on the Pi:

```bash
python3 embedded/final_code.py
```

This script uploads to Firebase at 1 Hz and sets:
- `fall`, `event`, `fall_state`
- `sleepwalking`, `sleep_event`, `sleep_state`
- `tmp_die_c` and `device_on_person`

### 3) Backend (Optional)

If you are using any backend utilities, run them from the `backend/` folder.
Most of the live UI functionality works directly from Firebase without a
separate server.

---

## Future Extensions
Possible future improvements include:
- Long-term data analytics and trend detection using LLM to identify when sleepwalking trends become a concern to alert doctors.
<<<<<<< HEAD
- Machine Learning to process thermo sensor data to accurately differentiate surrounding temperature vs body heat.
=======
>>>>>>> 607e344 (fixed ML bugs)
- In the event that the device disconnects from wifi, the detector will start to buzz loudly in the event of a fall to alert their caregivers.
