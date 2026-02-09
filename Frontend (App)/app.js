const statusText = document.getElementById("statusText");
const statusMeta = document.getElementById("statusMeta");
const statusDot = document.getElementById("statusDot");
const weeklyCount = document.getElementById("weeklyCount");
const monthlyCount = document.getElementById("monthlyCount");
const doctorNotes = document.getElementById("doctorNotes");
const alertEmpty = document.getElementById("alertEmpty");
const alertList = document.getElementById("alertList");
const triggerSleep = document.getElementById("triggerSleep");
const resolveSleep = document.getElementById("resolveSleep");
const triggerFall = document.getElementById("triggerFall");
const resetCounts = document.getElementById("resetCounts");
const fallOverlay = document.getElementById("fallOverlay");
const acknowledgeBtn = document.getElementById("acknowledge");
const deviceStatus = document.getElementById("deviceStatus");
const deviceMeta = document.getElementById("deviceMeta");
const deviceDot = document.getElementById("deviceDot");
const deviceOn = document.getElementById("deviceOn");
const deviceOff = document.getElementById("deviceOff");
const speedButtons = document.querySelectorAll("[data-speed]");

const DB_URL = "https://embedded-zenith-default-rtdb.firebaseio.com/latest.json";
let lastTs = null;
let speed = 1;
let activeFallAlert = null;
let activeSleepAlert = null;
let weeklyTotal = 0;
let monthlyTotal = 0;
let lastFallTs = null;

const FIREBASE_DB = "https://embedded-zenith-default-rtdb.firebaseio.com";
const LATEST_URL = `${FIREBASE_DB}/latest.json`;

const escalation = {
  sleepwalkNotice: "Sleepwalking detected. Monitoring closely.",
};


// Replace handleNewData and pollLatest with this unified logic
function handleNewData(data) {
    lastTs = data.ts;

    // 1. Sync On-Person Status (Temperature Logic)
    if (typeof data.device_on_person === "boolean") {
        setDeviceStatus(data.device_on_person);
    }

    // 2. Logic for Falls
    // Matches both "FALL" and "FALL_DETECTED" for safety
    const isFall = data.fall === true || data.event === "FALL" || data.event === "FALL_DETECTED";
    
    // 3. Logic for Sleepwalking
    const isSleepwalking = data.event === "SLEEPWALKING" || data.fall_state === "MOVING";

    // 4. Update UI based on logic
    if (isFall && !activeFallAlert) {
        triggerFallEvent();
    }

    if (isSleepwalking) {
        if (!activeSleepAlert) triggerSleepwalk();
    } else if (activeSleepAlert && data.fall_state === "STATIONARY") {
        resolveSleepwalk();
    }

    // 5. Update Telemetry with Temperature
    const az = data.accel_mps2?.z?.toFixed(2) || "0.00";
    const temp = data.tmp_die_c ? data.tmp_die_c.toFixed(1) : "--";
    statusMeta.textContent = `Live: az=${az} | Temp=${temp}°C | ts=${lastTs.toFixed(2)}`;
}

// Optimized Unified Polling
async function pollFirebase() {
    try {
        // 'no-cache' ensures we don't get old data stuck in the browser
        const response = await fetch(DB_URL, { cache: "no-store" });
        if (!response.ok) throw new Error("Server unreachable");

        const data = await response.json();

        // Only update if the timestamp has changed
        if (data && data.ts !== lastTs) {
            handleNewData(data);
        }
    } catch (error) {
        console.error("Fetch error:", error);
        statusMeta.textContent = "Offline - Reconnecting...";
        statusDot.style.background = "#888";
    }

    // Polling rate adjusted by simulation speed (default 500ms)
    setTimeout(pollFirebase, 500 / speed);
}



function setStatus(state, meta, color) {
  statusText.textContent = state;
  statusMeta.textContent = meta;
  statusDot.style.background = color;
  statusDot.style.boxShadow = `0 0 0 6px ${color}33`;
}

function addAlert(title, body) {
  alertEmpty.style.display = "none";
  const card = document.createElement("div");
  card.className = "alert";
  card.innerHTML = `<div class="alert__title">${title}</div><div>${body}</div>`;
  alertList.prepend(card);
  return card;
}

function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function updateMockStats() {
  weeklyCount.textContent = weeklyTotal;
  monthlyCount.textContent = monthlyTotal;

  doctorNotes.innerHTML = "";
  const stored = JSON.parse(localStorage.getItem("zenith_doctor_notes") || "[]");
  const notes = stored.length
    ? stored
    : [
        "Patient reported mild restlessness at 2:10 AM.",
        "No fall incidents in the last 48 hours.",
        "Caregiver noted improved bedtime routine compliance.",
        "Follow-up recommended after 7 nights of monitoring.",
      ];
  notes.forEach((note) => {
    const item = document.createElement("li");
    item.textContent = note;
    doctorNotes.appendChild(item);
  });
}

function incrementCounters() {
  weeklyTotal += 1;
  monthlyTotal += 1;
  updateMockStats();
}

function triggerSleepwalk() {
  setStatus("Sleepwalking", "Movement detected. Care team notified.", "#f2c85b");
  if (!activeSleepAlert) {
    activeSleepAlert = addAlert("Sleepwalking", escalation.sleepwalkNotice);
    incrementCounters();
  }
}

function resolveSleepwalk() {
  if (activeSleepAlert) {
    activeSleepAlert.remove();
    activeSleepAlert = null;
  }
  if (!alertList.children.length) {
    alertEmpty.style.display = "block";
  }
  setStatus("Normal", "Sleepwalking ended. Monitoring continues.", "#3fc06a");
}

function triggerFallEvent() {
  setStatus("Fall detected", "Awaiting acknowledgment.", "#d64545");
  activeFallAlert = addAlert("Fall detected", "Fall detected. Awaiting acknowledgment.");
  if (!activeSleepAlert) {
    incrementCounters();
  }
  fallOverlay.hidden = false;
}

function setDeviceStatus(isOnPerson) {
  if (isOnPerson) {
    deviceStatus.textContent = "On person";
    deviceMeta.textContent = "Signal stable.";
    deviceDot.style.background = "#3fc06a";
    deviceDot.style.boxShadow = "0 0 0 6px rgba(63, 192, 106, 0.15)";
  } else {
    deviceStatus.textContent = "Off person";
    deviceMeta.textContent = "No contact detected. Please check device.";
    deviceDot.style.background = "#d64545";
    deviceDot.style.boxShadow = "0 0 0 6px rgba(214, 69, 69, 0.15)";
  }
}

function acknowledgeFall() {
  fallOverlay.hidden = true;
  if (activeFallAlert) {
    activeFallAlert.remove();
    activeFallAlert = null;
  }
  if (!alertList.children.length) {
    alertEmpty.style.display = "block";
  }
  setStatus("Monitoring", "Fall acknowledged. Monitoring continues.", "#f2c85b");
}

// Event listener 
speedButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    speed = Number(btn.dataset.speed) || 1;
    addAlert("Simulation speed", `Speed set to ${speed}x.`);
  });
});

// Manual overwrite 
triggerSleep.addEventListener("click", triggerSleepwalk);
resolveSleep.addEventListener("click", resolveSleepwalk);
triggerFall.addEventListener("click", triggerFallEvent);
acknowledgeBtn.addEventListener("click", acknowledgeFall);
resetCounts.addEventListener("click", () => {
  weeklyTotal = 0;
  monthlyTotal = 0;
  updateMockStats();
});
deviceOn.addEventListener("click", () => setDeviceStatus(true));
deviceOff.addEventListener("click", () => setDeviceStatus(false));

updateMockStats();
setStatus("Normal", "No alerts in the last hour.", "#3fc06a");
setDeviceStatus(true);

async function pollLatest() {
  try {
    const response = await fetch(LATEST_URL, { cache: "no-store" });
    if (!response.ok) return;
    const data = await response.json();
    if (!data) return;

    if (typeof data.device_on_person === "boolean") {
      setDeviceStatus(data.device_on_person);
    }

    if (data.fall) {
      const ts = data.ts || Date.now();
      if (ts !== lastFallTs) {
        lastFallTs = ts;
        triggerFallEvent();
      }
    }
  } catch (error) {
    // Silent fail for demo mode
  }
}


pollFirebase();
