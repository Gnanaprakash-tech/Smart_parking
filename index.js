// index.js - Dashboard Counts with Live API Integration
const API_ENDPOINTS = {
  slotsStatus: "http://localhost:5006/api/slots/status"
};

console.log("index.js loaded");

// Function to fetch slot counts from backend API
async function fetchSlotCounts() {
  try {
    const response = await fetch(API_ENDPOINTS.slotsStatus);
    const data = await response.json();
    
    if (data.success) {
      // Calculate counts from slots data
      const counts = {
        total: data.total_slots || 0,
        available: data.total_available || 0,
        reserved: data.total_reserved || 0,
        occupied: 0  // Calculate from hardware_occupied if needed
      };
      
      // Count occupied slots from actual slot data
      if (data.slots) {
        counts.occupied = data.slots.filter(slot => 
          slot.hardware_occupied === true
        ).length;
      }
      
      // Update dashboard counts
      updateDashboardUI(counts);
      
      // Store in localStorage for quick access
      localStorage.setItem("dashboardCounts", JSON.stringify(counts));
      
      console.log("✅ Dashboard counts updated:", counts);
      return counts;
    } else {
      console.error("❌ Failed to fetch slot counts:", data.error);
      return null;
    }
  } catch (error) {
    console.error("❌ Error fetching slot counts:", error);
    
    // Fallback to localStorage if API fails
    const cachedData = JSON.parse(localStorage.getItem("dashboardCounts"));
    if (cachedData) {
      console.log("⚠️ Using cached data from localStorage");
      updateDashboardUI(cachedData);
    }
    return null;
  }
}

// Function to update dashboard UI elements
function updateDashboardUI(counts) {
  const totalEl = document.getElementById("Total-count");
  const availableEl = document.getElementById("available-count");
  const reservedEl = document.getElementById("reserved-count");
  const occupiedEl = document.getElementById("occupied-count");
  
  if (totalEl) totalEl.innerText = counts.total;
  if (availableEl) availableEl.innerText = counts.available;
  if (reservedEl) reservedEl.innerText = counts.reserved;
  if (occupiedEl) occupiedEl.innerText = counts.occupied;
}

// Initialize dashboard on page load
document.addEventListener("DOMContentLoaded", async () => {
  console.log("📊 Initializing dashboard...");
  
  // Try to fetch live data from API
  await fetchSlotCounts();
  
  // Auto-refresh every 5 seconds to keep dashboard updated
  setInterval(async () => {
    await fetchSlotCounts();
  }, 5000);  // Refresh every 5 seconds
  
  console.log("✅ Dashboard initialized with auto-refresh");
});

// Optional: Expose function globally for manual refresh
window.refreshDashboard = fetchSlotCounts;