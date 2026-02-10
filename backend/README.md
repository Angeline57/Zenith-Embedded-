# ☁️ Backend & Cloud Communication

The backend serves as the centralized logic engine for SafeSleep, bridging the gap between high-frequency embedded sensor data and the user-facing dashboard.

## 🔒 Security & Authentication
To maintain patient privacy and database integrity, all cloud interactions are strictly authenticated:

* **Service Account Authorization:** The backend utilizes a Google Service Account (`keyfile.json`) to establish an **AuthorizedSession**.
* **OAuth2 Protocol:** Instead of using static API keys, the system exchanges service credentials for short-lived **OAuth2 tokens**.
* **Scoped Permissions:** The backend is restricted to the `firebase.database` scope, ensuring it can only interact with the relevant Realtime Database nodes.

## 📡 Communication Protocol
While MQTT is common in IoT, SafeSleep utilizes **HTTP (REST)** for cloud synchronization for the following reasons:

* **Stateless Reliability:** Given the critical nature of fall detection, HTTP's request-response pattern ensures that the backend explicitly acknowledges data receipt.
* **Cloud Compatibility:** Firebase Realtime Database is natively optimized for RESTful interaction, allowing for easier integration with the `AuthorizedSession` logic.
* **Frequency Limitations:** Both MQTT and HTTP face overhead constraints at extremely high frequencies (e.g., >100Hz raw IMU data). To solve this, the **Edge Layer** handles high-frequency sampling and local processing, while the **Backend** utilizes HTTP to sync the *results* and *status updates* at a sustainable rate.



## 🛠️ Core Functions
1.  **Data Retrieval (GET):** Pulls the latest raw temperature and sensor data from the `/latest` node.
2.  **Status Calculation:** Processes die temperature ($T_{die}$) to determine if the device is currently "On-Person."
3.  **State Synchronization (PATCH):** Updates the database with processed flags. Unlike `PUT`, **PATCH** is used to surgically update specific keys (like `on_person`) without overwriting the raw IMU data provided by the Pi.

## 🚀 How to Run
1. Ensure your `keyfile.json` is in this directory.
2. Install dependencies: `pip install google-auth requests`
3. Run the engine: `python final_backend.py`