const commandKey = "zenith_sim_command";

function sendCommand(type, payload = {}) {
  const command = {
    type,
    payload,
    ts: Date.now(),
  };
  localStorage.setItem(commandKey, JSON.stringify(command));
}

document.getElementById("triggerSleep").addEventListener("click", () => {
  sendCommand("triggerSleep");
});

document.getElementById("resolveSleep").addEventListener("click", () => {
  sendCommand("resolveSleep");
});

document.getElementById("triggerFall").addEventListener("click", () => {
  sendCommand("triggerFall");
});

document.getElementById("resetCounts").addEventListener("click", () => {
  sendCommand("resetCounts");
});

document.getElementById("deviceOn").addEventListener("click", () => {
  sendCommand("deviceOn");
});

document.getElementById("deviceOff").addEventListener("click", () => {
  sendCommand("deviceOff");
});

document.querySelectorAll("[data-speed]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const speed = Number(btn.dataset.speed) || 1;
    sendCommand("speed", { speed });
  });
});
