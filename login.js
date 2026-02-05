document.addEventListener("DOMContentLoaded", function () {

  const form = document.getElementById("login-form");
  const errorMsg = document.getElementById("error-msg");

  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value.trim();

    errorMsg.innerText = "";

    // =====================
    // VALIDATION
    // =====================
    if (!email || !password) {
      errorMsg.innerText = "Please enter email and password";
      return;
    }

    // =====================
    // API CALL
    // =====================
    try {
      const response = await fetch("http://localhost:5006/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: email,
          password: password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        errorMsg.innerText = data.message || "Invalid email or password";
        return;
      }

      // =====================
      // SUCCESS
      // =====================
      localStorage.setItem("user", JSON.stringify(data.user));
      if (data.token) {
        localStorage.setItem("token", data.token);
      }

      alert("Login successful!");
      window.location.href = "slots.html";

    } catch (error) {
      console.error(error);
      errorMsg.innerText = "Server error. Try again later.";
    }
  });

});
