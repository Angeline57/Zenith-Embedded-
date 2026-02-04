const statusText = document.getElementById("statusText");
const statusMeta = document.getElementById("statusMeta");
const statusDot = document.getElementById("statusDot");
const weeklyCount = document.getElementById("weeklyCount");
const monthlyCount = document.getElementById("monthlyCount");
const timelineBars = document.getElementById("timelineBars");
const alertEmpty = document.getElementById("alertEmpty");
const alertList = document.getElementById("alertList");
const triggerSleep = document.getElementById("triggerSleep");
const resolveSleep = document.getElementById("resolveSleep");
const triggerFall = document.getElementById("triggerFall");
const fallOverlay = document.getElementById("fallOverlay");
const acknowledgeBtn = document.getElementById("acknowledge");
const speedButtons = document.querySelectorAll("[data-speed]");

let speed = 1;
let activeFallAlert = null;
let activeSleepAlert = null;

const escalation = {
  sleepwalkNotice: "Sleepwalking detected. Monitoring closely.",
};

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
  const weekly = randomInt(2, 7);
  const monthly = weekly + randomInt(4, 10);
  weeklyCount.textContent = weekly;
  monthlyCount.textContent = monthly;

  timelineBars.innerHTML = "";
  for (let i = 0; i < 7; i += 1) {
    const bar = document.createElement("div");
    bar.className = "timeline__bar";
    bar.style.height = `${randomInt(25, 95)}%`;
    timelineBars.appendChild(bar);
  }
}

function triggerSleepwalk() {
  setStatus("Sleepwalking", "Movement detected. Care team notified.", "#f2c85b");
  if (!activeSleepAlert) {
    activeSleepAlert = addAlert("Sleepwalking", escalation.sleepwalkNotice);
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
  fallOverlay.hidden = false;
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

speedButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    speed = Number(btn.dataset.speed) || 1;
    addAlert("Simulation speed", `Speed set to ${speed}x.`);
  });
});

triggerSleep.addEventListener("click", triggerSleepwalk);
resolveSleep.addEventListener("click", resolveSleepwalk);
triggerFall.addEventListener("click", triggerFallEvent);
acknowledgeBtn.addEventListener("click", acknowledgeFall);

updateMockStats();
setStatus("Normal", "No alerts in the last hour.", "#3fc06a");
