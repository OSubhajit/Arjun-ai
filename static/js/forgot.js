/**
 * forgot.js — send OTP + reset password flow.
 */

function showMsg(text, type) {
  var el     = document.getElementById("msg");
  el.textContent = text;
  el.className   = "simple-msg " + type;
}

function checkStrength() {
  var val = document.getElementById("password").value;
  var bar = document.getElementById("bar");
  var s   = 0;
  if (val.length > 6)            s++;
  if (/[A-Z]/.test(val))         s++;
  if (/[0-9]/.test(val))         s++;
  if (/[^A-Za-z0-9]/.test(val)) s++;
  bar.style.width      = (s * 25) + "%";
  bar.style.background = ["", "#e07070", "#f7931e", "#f0d060", "#7ab88a"][s];
}

async function sendOTP() {
  var email = document.getElementById("email").value.trim();
  if (!email) { showMsg("Please enter your email.", "error"); return; }

  var btn     = document.getElementById("sendOtpBtn");
  btn.disabled    = true;
  btn.textContent = "Sending…";

  try {
    var res  = await fetch("/forgot", {
      method : "POST",
      headers: { "Content-Type": "application/json" },
      body   : JSON.stringify({ action: "send_otp", email }),
    });
    var data = await res.json();
    showMsg(
      data.success ? (data.message || "OTP sent!") : (data.message || "Failed."),
      data.success ? "success" : "error"
    );
  } catch (_) {
    showMsg("Connection failed. Try again.", "error");
  }

  btn.disabled    = false;
  btn.textContent = "Send OTP";
}

async function resetPassword() {
  var email    = document.getElementById("email").value.trim();
  var otp      = document.getElementById("otp").value.trim();
  var password = document.getElementById("password").value;

  if (!email || !otp || !password) { showMsg("Please fill all fields.", "error"); return; }
  if (password.length < 8) { showMsg("Password must be at least 8 characters.", "error"); return; }

  var btn     = document.getElementById("resetBtn");
  btn.disabled    = true;
  btn.textContent = "Resetting…";

  try {
    var res  = await fetch("/forgot", {
      method : "POST",
      headers: { "Content-Type": "application/json" },
      body   : JSON.stringify({ action: "reset_password", email, otp, password }),
    });
    var data = await res.json();
    if (data.success) {
      showMsg("Password updated! Redirecting…", "success");
      setTimeout(function () { window.location.href = "/"; }, 1500);
    } else {
      showMsg(data.message || "Invalid OTP.", "error");
    }
  } catch (_) {
    showMsg("Connection failed. Try again.", "error");
  }

  btn.disabled    = false;
  btn.textContent = "Reset Password";
}
