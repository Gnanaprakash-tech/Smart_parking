// =====================
// SHOW / HIDE STAFF ID
// =====================
function toggleStaffId() {
  const role = document.getElementById("role");
  const userid = document.getElementById("userid");
  if (!role || !userid) return;
  userid.style.display = role.value === "staff" ? "block" : "none";
  if (role.value !== "staff") userid.value = "";
}

// Run when page loads
window.addEventListener("DOMContentLoaded", () => {
  toggleStaffId();
});

// =====================
// SIGNUP FUNCTION
// =====================
async function signup() {
  const form = document.getElementById("signup-form");
  const errorMsg = document.getElementById("error-msg");
  const email = document.getElementById("email")?.value.trim() || "";
  const password = document.getElementById("password")?.value || "";
  const confirm = document.getElementById("confirm")?.value || "";
  const role = document.getElementById("role")?.value || "";

  errorMsg.textContent = "";

  if (!email) {
    errorMsg.textContent = "Please enter an email.";
    return;
  }
  if (password.length < 6) {
    errorMsg.textContent = "Password must be at least 6 characters.";
    return;
  }
  if (password !== confirm) {
    errorMsg.textContent = "Passwords do not match.";
    return;
  }
  if (role === "staff") {
    const userid = document.getElementById("userid")?.value.trim() || "";
    if (!userid) {
      errorMsg.textContent = "Please enter Staff ID.";
      return;
    }
  }
  // =====================
// API CALL - REGISTER
// =====================
try {
  const response = await fetch("http://localhost:5006/auth/register", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      email: email,
      password: password,
      role: role,
      userid: role === "staff" ? userid : null,
    }),
  });

  const data = await response.json();

  if (!response.ok) {
    errorMsg.textContent = data.message || "Signup failed.";
    return;
  }

  alert("Signup successful!");

  // optional: save backend response
  localStorage.setItem("loggedInUser", JSON.stringify(data.user));

  window.location.href = "index.html";

} catch (error) {
  console.error(error);
  errorMsg.textContent = "Server error. Please try again later.";
}


  

  
  
}