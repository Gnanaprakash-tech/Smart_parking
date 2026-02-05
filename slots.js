console.log("slots.js loaded");
const storage = sessionStorage;

// -----------------------------
// CURRENT USER
// -----------------------------
const currentUser = JSON.parse(localStorage.getItem("user"));

if (!currentUser) {
  alert("Please login first");
  window.location.href = "login.html";
}

// -----------------------------
// ROLE CHECK
// -----------------------------
const reserveBtn = document.querySelector(".reserve-main-btn");
const loading = document.getElementById("loading");

if (currentUser.role !== "staff" && reserveBtn) {
  reserveBtn.style.display = "none";
}

// -----------------------------
// CONFIG
// -----------------------------
const totalSlots = 5;
const RESERVATION_TIME = 10 * 60;

// one-user-one-slot key
const userKey = "reservedSlot_" + currentUser.email;

// -----------------------------
// ELEMENTS
// -----------------------------
const parkingLot = document.getElementById("parkingLot");
let selectedSlot = null;

// -----------------------------
// CREATE SLOTS
// -----------------------------
for (let i = 1; i <= totalSlots; i++) {
  const slot = document.createElement("div");
  slot.className = "slot";
  slot.dataset.status = "available";
  slot.dataset.slotNumber = i;
  slot.innerText = i;

  slot.onclick = () => {
    if (slot.dataset.status === "reserved") return;

    document.querySelectorAll(".slot").forEach(s => s.classList.remove("selected"));
    selectedSlot = slot;
    slot.classList.add("selected");
  };

  parkingLot.appendChild(slot);
}

// -----------------------------
// FETCH SLOTS STATUS
// -----------------------------
function fetchSlotStatus() {
  fetch("http://localhost:5006/auth/slots_status")
    .then(res => res.json())
    .then(data => {
      data.forEach(s => {
        const slotEl = document.querySelector(`.slot[data-slot-number="${s.slot}"]`);
        if (slotEl) {
          if (s.status === "reserved") {
            slotEl.dataset.status = "reserved";
            slotEl.classList.add("reserved");
            slotEl.innerText = "RESERVED";
          } else {
            slotEl.dataset.status = "available";
            slotEl.classList.remove("reserved");
            slotEl.innerText = s.slot;
          }
        }
      });
      updateCounts();
    })
    .catch(err => console.error("Slot status error:", err));
}

// Call on page load
window.addEventListener("DOMContentLoaded", fetchSlotStatus);

// -----------------------------
// UPDATE COUNTS
// -----------------------------
function updateCounts() {
  const slots = document.querySelectorAll(".slot");
  let reserved = 0;

  slots.forEach(s => {
    if (s.dataset.status === "reserved") reserved++;
  });

  const total = slots.length;
  const available = total - reserved;

  document.getElementById("total-slots").innerText = total;
  document.getElementById("reserved-slots").innerText = reserved;
  document.getElementById("available-slots").innerText = available;
  document.getElementById("occupied-slots").innerText = 0;

  localStorage.setItem(
    "dashboardCounts",
    JSON.stringify({ total, reserved, available, occupied: 0 })
  );
}

updateCounts();

// -----------------------------
// RESERVE SLOT
// -----------------------------
function reserveSelectedSlot() {
  if (currentUser.role !== "staff") {
    alert("Only staff can reserve slots");
    return;
  }

  if (sessionStorage.getItem(userKey)) {
    alert("You already reserved one slot this session");
    return;
  }

  if (!selectedSlot) {
    alert("Select a slot first");
    return;
  }

  loading.classList.remove("hidden");
  reserveBtn.disabled = true;

  setTimeout(() => {
    let timeLeft = RESERVATION_TIME;
    const slot = selectedSlot;
    selectedSlot = null;

    // -----------------------------
    // CALL RESERVE-SLOT API
    // -----------------------------
    fetch("http://localhost:5006/auth/reserve-slot", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${localStorage.getItem("token")}`
      },
      body: JSON.stringify({
        slot: slot.dataset.slotNumber
      })
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          sessionStorage.setItem(userKey, slot.dataset.slotNumber);
          slot.dataset.status = "reserved";
          slot.classList.add("reserved");
          slot.classList.remove("selected");

          updateCounts();
        } else {
          alert(data.error || "Slot already reserved");
        }

        loading.classList.add("hidden");
        reserveBtn.disabled = false;
      })
      .catch(err => {
        console.error(err);
        loading.classList.add("hidden");
        reserveBtn.disabled = false;
      });

    setInterval(fetchSlotStatus, 5000); // refresh every 5 sec

    updateCounts();
    loading.classList.add("hidden");
    reserveBtn.disabled = false;

    const timer = setInterval(() => {
      const min = Math.floor(timeLeft / 60);
      const sec = timeLeft % 60;

      slot.innerHTML = `
        <div class="reserved-label">RESERVED</div>
        <div class="timer-text">${min}:${sec.toString().padStart(2, "0")}</div>
      `;

      timeLeft--;

      if (timeLeft < 0) {
        clearInterval(timer);
        sessionStorage.removeItem(userKey);

        slot.dataset.status = "available";
        slot.classList.remove("reserved");
        slot.innerText = slot.dataset.slotNumber;

        updateCounts();
      }
    }, 1000);
  }, 1200);
}

// -----------------------------
// HARDWARE INTEGRATION
// -----------------------------

// Fetch hardware reserve signals every 5 seconds
async function getReserveSignal() {
  try {
    const res = await fetch("http://localhost:5006/hardware/reserve-signal");
    const data = await res.json();

    if (!res.ok) {
      console.error(data.message || "Failed to fetch reserve signals");
      return;
    }

    console.log("Hardware reserve signals:", data);
    // Optional: you can highlight slots if hardware reserved
  } catch (err) {
    console.error("Reserve signal error:", err);
  }
}
setInterval(getReserveSignal, 5000);
window.addEventListener("DOMContentLoaded", getReserveSignal);

// Send sensor updates (call this wherever sensor data is available)
async function sendSensorUpdate(sensorData) {
  try {
    const res = await fetch("http://localhost:5006/hardware/sensor-update", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(sensorData)
    });
    const data = await res.json();

    if (!res.ok) {
      console.error(data.message || "Failed sensor update");
      return;
    }

    console.log("Sensor updated:", data);
  } catch (err) {
    console.error("Sensor update error:", err);
  }
}

// -----------------------------
// LOGOUT
// -----------------------------
function logout() {
  localStorage.clear();
  window.location.href = "index.html";
}
