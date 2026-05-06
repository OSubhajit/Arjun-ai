"""
blueprints/auth/routes.py — authentication: login, register, forgot-password, logout.
"""
import logging

import bcrypt
from flask import Blueprint, jsonify, redirect, render_template, request, session
from markupsafe import escape as html_escape
from pymongo.errors import DuplicateKeyError

from extensions import users_col
from utils.email import send_email_otp
from utils.security import (
    generate_csrf_token,
    generate_otp,
    get_client_ip,
    is_login_rate_limited,
    is_rate_limited,
    is_valid_email,
    otp_delete,
    otp_get,
    otp_record_failed_attempt,
    otp_save,
    validate_csrf,
    verify_otp_value,
)

log = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def sanitize_name(name: str) -> str:
    return str(html_escape(name.strip()))[:100]


def _require_json():
    if not request.is_json:
        return jsonify({"success": False, "message": "JSON required"}), 415
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "message": "Invalid request body"}), 400
    return data


# ── Login ─────────────────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if "user" in session:
            return redirect("/chat")
        return render_template("login.html", csrf_token=generate_csrf_token())

    if not validate_csrf():
        return jsonify({"success": False, "message": "Invalid or missing CSRF token."}), 403

    data = _require_json()
    if isinstance(data, tuple):
        return data

    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")
    remember = bool(data.get("rememberMe", False))

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password required"})

    if not is_valid_email(email):
        return jsonify({"success": False, "message": "Invalid email address"})

    if is_login_rate_limited(get_client_ip()):
        return jsonify({"success": False, "message": "Too many login attempts. Please wait 15 minutes."})

    user = users_col.find_one({"email": email})
    if not user or not bcrypt.checkpw(password.encode(), user["password"].encode()):
        return jsonify({"success": False, "message": "Invalid credentials"})

    session.clear()
    session.permanent = remember
    session["user"]   = email
    session["name"]   = user["name"]
    log.info("Login: %s", email)
    return jsonify({"success": True, "redirect": "/chat"})


# ── Register ──────────────────────────────────────────────────────────────────

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html", csrf_token=generate_csrf_token())

    if not validate_csrf():
        return jsonify({"success": False, "message": "Invalid or missing CSRF token."}), 403

    data = _require_json()
    if isinstance(data, tuple):
        return data

    action = data.get("action")
    email  = data.get("email", "").strip().lower()

    if not email or not action:
        return jsonify({"success": False, "message": "Email and action required"})

    if not is_valid_email(email):
        return jsonify({"success": False, "message": "Invalid email address"})

    # ── Step 1: send OTP ──────────────────────────────────────────────────────
    if action == "send_otp":
        name     = sanitize_name(data.get("name", ""))
        password = data.get("password", "")

        if not name or not password:
            return jsonify({"success": False, "message": "All fields required"})

        if len(password) < 8:
            return jsonify({"success": False, "message": "Password must be at least 8 characters"})

        if is_rate_limited(get_client_ip()):
            return jsonify({"success": False, "message": "Too many OTP requests. Please wait 10 minutes."})

        if users_col.find_one({"email": email}):
            return jsonify({"success": False, "message": "An account with this email already exists."})

        otp             = generate_otp()
        hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        otp_save(email, {"otp": otp, "name": name, "password": hashed_password, "type": "register"})

        if not send_email_otp(email, otp, name=name):
            otp_delete(email)
            return jsonify({"success": False, "message": "Failed to send OTP. Check GMAIL_SCRIPT_URL."})

        return jsonify({"success": True, "message": "OTP sent to your email!"})

    # ── Step 2: verify OTP ────────────────────────────────────────────────────
    if action == "verify_otp":
        user_data = otp_get(email)

        if not user_data:
            return jsonify({"success": False, "message": "OTP not found or expired. Please request a new one."})

        if user_data.get("type") != "register":
            return jsonify({"success": False, "message": "Invalid OTP type."})

        if user_data.get("attempts", 0) >= 5:
            otp_delete(email)
            return jsonify({"success": False, "message": "Too many failed attempts. Please request a new OTP."})

        if not verify_otp_value(user_data["otp"], data.get("otp", "")):
            remaining = max(0, 5 - otp_record_failed_attempt(email))
            return jsonify({"success": False, "message": f"Invalid OTP. {remaining} attempt(s) remaining."})

        try:
            users_col.insert_one({
                "email"       : email,
                "name"        : user_data["name"],
                "password"    : user_data["password"],
                "chat_history": [],
                "notes"       : [],
            })
        except DuplicateKeyError:
            otp_delete(email)
            return jsonify({"success": False, "message": "User already exists. Please log in."})

        otp_delete(email)
        session.clear()
        session.permanent = True
        session["user"]   = email
        session["name"]   = user_data["name"]
        log.info("Registered: %s", email)
        return jsonify({"success": True, "redirect": "/chat"})

    return jsonify({"success": False, "message": "Invalid action"})


# ── Forgot password ───────────────────────────────────────────────────────────

@auth_bp.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "GET":
        return render_template("forgot.html", csrf_token=generate_csrf_token())

    if not validate_csrf():
        return jsonify({"success": False, "message": "Invalid or missing CSRF token."}), 403

    data = _require_json()
    if isinstance(data, tuple):
        return data

    action = data.get("action")
    email  = data.get("email", "").strip().lower()

    if not email or not is_valid_email(email):
        return jsonify({"success": False, "message": "Valid email is required"})

    if action == "send_otp":
        if is_rate_limited(get_client_ip()):
            return jsonify({"success": False, "message": "Too many OTP requests. Please wait 10 minutes."})

        # Intentionally don't reveal whether email exists
        user = users_col.find_one({"email": email})
        if user:
            otp = generate_otp()
            otp_save(email, {"otp": otp, "name": user.get("name", "User"), "type": "forgot"})
            send_email_otp(email, otp, name=user.get("name", "User"))

        return jsonify({"success": True, "message": "If this email is registered, you'll receive an OTP shortly."})

    if action == "reset_password":
        new_password = data.get("password", "")
        otp          = data.get("otp", "")

        if not new_password:
            return jsonify({"success": False, "message": "New password is required"})
        if len(new_password) < 8:
            return jsonify({"success": False, "message": "Password must be at least 8 characters"})

        user_data = otp_get(email)

        if user_data and user_data.get("attempts", 0) >= 5:
            otp_delete(email)
            return jsonify({"success": False, "message": "Too many failed attempts. Please request a new OTP."})

        if not user_data or not verify_otp_value(user_data.get("otp", ""), otp):
            if user_data:
                remaining = max(0, 5 - otp_record_failed_attempt(email))
                return jsonify({"success": False, "message": f"Invalid OTP. {remaining} attempt(s) remaining."})
            return jsonify({"success": False, "message": "Invalid or expired OTP"})

        if user_data.get("type") != "forgot":
            return jsonify({"success": False, "message": "Invalid OTP type"})

        hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        users_col.update_one({"email": email}, {"$set": {"password": hashed}})
        otp_delete(email)
        log.info("Password reset: %s", email)
        return jsonify({"success": True})

    return jsonify({"success": False, "message": "Invalid action"})


# ── Logout ────────────────────────────────────────────────────────────────────

@auth_bp.route("/logout", methods=["POST"])
def logout():
    if not validate_csrf():
        return jsonify({"success": False, "message": "Invalid or missing CSRF token."}), 403
    log.info("Logout: %s", session.get("user"))
    session.clear()
    return jsonify({"success": True, "redirect": "/"})
