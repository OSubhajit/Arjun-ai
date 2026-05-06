/**
 * register.js — two-step registration flow (send OTP → verify OTP).
 */

let _registeredEmail = "";

function showMsg(text, type) {
  var el = document.getElementById("msg");
  el.textContent = text;
  el.className   = "msg " + type;
}

function clearMsg() {
  document.getElementById("msg").textContent = "";
}

function goBack() {
  document.getElementById("step1-section").style.display = "block";
  document.getElementById("step2-section").classList.remove("visible");
  clearMsg();
}

// ── Send OTP ──────────────────────────────────────────────────────────────────
async function sendOTP() {
  clearMsg();

  var name     = document.getElementById("name").value.trim();
  var email    = document.getElementById("email").value.trim();
  var password = document.getElementById("password").value;
  var btn      = document.getElementById("sendOtpBtn");

  if (!name || !email || !password) {
    showMsg("All fields are required.", "error");
    return;
  }

  btn.disabled    = true;
  btn.textContent = "Sending…";

  try {
    var res = await fetch("/register", {
      method : "POST",
      headers: { "Content-Type": "application/json" },
      body   : JSON.stringify({ action: "send_otp", name, email, password }),
    });

    var data = await res.json();

    if (data.success) {
      _registeredEmail = email;
      document.getElementById("step1-section").style.display = "none";
      document.getElementById("step2-section").classList.add("visible");
      document.getElementById("email-display").textContent = email;
      showMsg("OTP sent! Check your inbox.", "success");
    } else {
      showMsg(data.message || "Failed to send OTP.", "error");
    }
  } catch (_) {
    showMsg("Connection failed. Please try again.", "error");
  }

  btn.disabled    = false;
  btn.textContent = "Send OTP to Email ✦";
}

// ── Verify OTP ────────────────────────────────────────────────────────────────
async function verifyOTP() {
  clearMsg();

  var otp   = document.getElementById("otp").value.trim();
  var email = document.getElementById("email").value.trim() || _registeredEmail;
  var btn   = document.getElementById("verifyBtn");

  if (!otp) { showMsg("Please enter the OTP.", "error"); return; }

  btn.disabled    = true;
  btn.textContent = "Verifying…";

  try {
    var res = await fetch("/register", {
      method : "POST",
      headers: { "Content-Type": "application/json" },
      body   : JSON.stringify({ action: "verify_otp", email, otp }),
    });

    var data = await res.json();

    if (data.success) {
      showMsg("Account created! Redirecting…", "success");
      setTimeout(function () { window.location.href = data.redirect || "/chat"; }, 1000);
    } else {
      showMsg(data.message || "Invalid OTP.", "error");
    }
  } catch (_) {
    showMsg("Connection failed. Please try again.", "error");
  }

  btn.disabled    = false;
  btn.textContent = "Verify & Create Account ✦";
}

// ── Resend OTP ────────────────────────────────────────────────────────────────
async function resendOTP() {
  clearMsg();

  var name     = document.getElementById("name").value.trim();
  var email    = document.getElementById("email").value.trim() || _registeredEmail;
  var password = document.getElementById("password").value;

  try {
    var res  = await fetch("/register", {
      method : "POST",
      headers: { "Content-Type": "application/json" },
      body   : JSON.stringify({ action: "send_otp", name, email, password }),
    });
    var data = await res.json();
    showMsg(data.success ? "OTP resent!" : (data.message || "Failed."), data.success ? "success" : "error");
  } catch (_) {
    showMsg("Connection failed.", "error");
  }
}
