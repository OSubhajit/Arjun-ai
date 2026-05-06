"""
blueprints/profile/routes.py — profile page, /api/profile, /api/conversations.
"""
import logging
import re

from flask import Blueprint, jsonify, redirect, render_template, request, session

from extensions import users_col
from utils.history import group_by_session
from utils.security import generate_csrf_token, validate_csrf

log = logging.getLogger(__name__)
profile_bp = Blueprint("profile", __name__)


@profile_bp.route("/profile")
def profile():
    if "user" not in session:
        return redirect("/")
    return render_template("profile.html", csrf_token=generate_csrf_token())


@profile_bp.route("/api/profile")
def api_profile():
    if "user" not in session:
        return jsonify({"error": "Not logged in"}), 401

    user_data = users_col.find_one(
        {"email": session["user"]},
        {"name": 1, "email": 1, "chat_history": {"$slice": -200}, "_id": 0},
    )
    if not user_data:
        return jsonify({"error": "User not found"}), 404

    history       = user_data.get("chat_history", [])
    conversations = group_by_session(history)

    return jsonify({
        "name"          : user_data.get("name", ""),
        "email"         : user_data.get("email", ""),
        "total_messages": len(history),
        "total_sessions": len(conversations),
        "conversations" : conversations,
    })


@profile_bp.route("/api/conversations")
def api_conversations():
    if "user" not in session:
        return jsonify({"conversations": []}), 401

    user_data = users_col.find_one(
        {"email": session["user"]},
        {"chat_history": {"$slice": -200}, "_id": 0},
    )
    if not user_data:
        return jsonify({"conversations": []})

    return jsonify({"conversations": group_by_session(user_data.get("chat_history", []))})


@profile_bp.route("/api/conversations/<path:conv_id>", methods=["DELETE"])
def delete_conversation(conv_id: str):
    if "user" not in session:
        return jsonify({"error": "Not logged in"}), 401

    if not validate_csrf():
        return jsonify({"error": "Invalid or missing CSRF token."}), 403

    is_session_id  = bool(re.match(r'^\d+$', conv_id))
    is_date_prefix = conv_id.startswith("date:")
    is_date_only   = bool(re.match(r'^\d{4}-\d{2}-\d{2}$', conv_id))

    if not (is_session_id or is_date_prefix or is_date_only):
        return jsonify({"error": "Invalid session identifier"}), 400

    if is_session_id:
        pull_filter = {"session_id": conv_id}
    elif is_date_prefix:
        date_val    = conv_id[5:]
        pull_filter = {
            "session_id": {"$exists": False},
            "timestamp" : {"$regex": f"^{re.escape(date_val)}"},
        }
    else:
        pull_filter = {"timestamp": {"$regex": f"^{re.escape(conv_id)}"}}

    result = users_col.update_one(
        {"email": session["user"]},
        {"$pull": {"chat_history": pull_filter}},
    )
    if result.matched_count == 0:
        return jsonify({"error": "User not found"}), 404

    log.info("Deleted conversation %s for %s", conv_id, session["user"])
    return jsonify({"success": True, "deleted_session": conv_id})
