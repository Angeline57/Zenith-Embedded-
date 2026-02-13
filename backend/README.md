# Backend & Cloud Communication

The backend serves as the centralized logic engine for Zenith Sleep, bridging the gap between embedded sensor data and the user-facing dashboards.

## Security & Authentication
To maintain patient privacy and database integrity, all cloud interactions are strictly authenticated:

* **Service Account Authorization:** The backend utilizes a Google Service Account (`embedded-zenith-firebase-adminsdk-fbsvc-92e37b3ef2.json`) to establish an **AuthorizedSession**.
* **OAuth2 Protocol:** Instead of using static API keys, the system exchanges service credentials for short-lived **OAuth2 tokens**.
* **Scoped Permissions:** The backend is restricted to the `firebase.database` scope, ensuring it can only interact with the relevant Realtime Database nodes.

## Communication Protocol
While MQTT is common in IoT, SafeSleep utilizes **HTTP (REST)** for cloud synchronization for the following reasons:

* **Stateless Reliability:** Given the critical nature of fall detection, HTTP's request-response pattern ensures that the backend explicitly acknowledges data receipt.
* **Cloud Compatibility:** Firebase Realtime Database is natively optimized for RESTful interaction, allowing for easier integration with the `AuthorizedSession` logic.
* **Frequency Limitations:** Both MQTT and HTTP face overhead constraints at extremely high frequencies (e.g., >100Hz raw IMU data). To solve this, the **Edge Layer** handles high-frequency sampling and local processing, while the **Backend** utilizes HTTP to sync the *results* and *status updates* at a sustainable rate.



## Core Functions
1. **Data Retrieval (GET):** Pulls the latest temperature and sensor data from `/latest.json`.
2. **Wear Status Calculation:** Computes `device_on_person` (ML-based if enabled, otherwise threshold-based).
3. **State Synchronization (PATCH):** Updates the database with `device_on_person` without overwriting IMU data.

## How to Run
1. Ensure your service account key is in this directory:
   `embedded-zenith-firebase-adminsdk-fbsvc-92e37b3ef2.json`
2. Install dependencies: `pip install google-auth requests`
3. Run the engine: `python3 final_backend.py`

## ML Wear Detection (Optional)
- `ML_device_worn.py` runs a standalone ML-based wear detector (polls Firebase + PATCHes `device_on_person`)
- `train_device_worn.py` trains the model on `fake_temp_data.csv` and exports weights to `ML_device_worn.py`
