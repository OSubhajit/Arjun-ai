"""
blueprints/main/routes.py — index redirect, static info pages, CSRF token endpoint.
"""
from flask import Blueprint, jsonify, redirect, render_template, session

from utils.security import generate_csrf_token

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    if "user" in session:
        return redirect("/chat")
    return redirect("/login")


@main_bp.route("/help")
def help_page():
    return render_template("help.html")


@main_bp.route("/privacy")
def privacy():
    return render_template("privacy.html")


@main_bp.route("/api/csrf-token")
def csrf_token_endpoint():
    return jsonify({"csrf_token": generate_csrf_token()})
