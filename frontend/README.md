# Frontend (Web Interface)
This frontend includes **two web experiences**:
1. **Marketing website** (public-facing)
2. **Live app UI** (caregiver-facing)

## Marketing website (frontend/marketing)
**Pages**
- `index.html` (marketing site with product story, features, video)
- `login.html` (role-based login)
- `doctor_dashboard.html` (doctor portal)
- `user_dashboard.html` (user portal, mirrors app experience)

**Website features**
- Benefits and feature accordion
- Marketing video embedded in the demo section
- Device mockups carousel
- Doctor dashboard with multi‑patient tabs (E. Johnson is connected)
- Doctor notes that sync to the app via shared storage
- User dashboard with live status, wear status, counts, and notes

## App UI (frontend/app)
**Pages**
- `app.html` (live dashboard)
- `login.html` (app login screen)
- `sim.html` (simulator controls)

**App features**
- Live fall + sleepwalking status (reads from Firebase `/latest.json`)
- Device wear status (uses `device_on_person` from backend)
- Device temperature display (uses `tmp_die_c` from backend)
- Sleepwalking counters (weekly / monthly)
- Notes from doctor (synced with doctor dashboard)
- “Last update” timestamp
- PWA support (manifest + service worker)
- Simulator controls (separate page)

## Data connections
- Firebase read: `https://embedded-zenith-default-rtdb.firebaseio.com/latest.json`
- Notes + counts sync between app and doctor dashboard via `localStorage` keys:
  - `zenith_shared_notes`
  - `zenith_sleepwalk_counts`

## Mock mode
Simulator controls (`sim.html`) can still be used for demos when backend data is unavailable.
