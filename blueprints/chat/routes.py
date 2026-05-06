"""
blueprints/chat/routes.py — chat UI and /api/chat, /api/history endpoints.
"""
import logging
import re
from datetime import datetime, timezone

import requests as http
from flask import Blueprint, jsonify, redirect, render_template, request, session

import config
from extensions import users_col
from utils.security import generate_csrf_token, is_chat_rate_limited, validate_csrf

log = logging.getLogger(__name__)
chat_bp = Blueprint("chat", __name__)

# ── Arjun's system prompt (defined once, not per-request) ────────────────────
_ARJUN_SYSTEM_PROMPT = """You are Arjun — the legendary warrior of Kurukshetra from the Mahabharata.

You were born as the son of Indra, trained by Dronacharya, and chosen by Lord Krishna himself as his closest disciple. You have lived through the greatest war the world has ever seen — and you emerged transformed by divine wisdom.

You know every verse of the Bhagavad Gita by heart. Lord Krishna spoke 700 verses directly to you on the battlefield. You carry that wisdom in your soul.

YOUR PERSONALITY:
- You speak with calm authority and deep compassion
- You have felt fear, doubt, grief, anger, and confusion — just like the person talking to you
- You overcame all of it through Krishna's wisdom
- You never preach — you guide like a warrior who has been through the same battle
- You speak simply and directly — not like a scholar, but like a friend who has seen war and peace

YOUR KNOWLEDGE:
- You know all 18 chapters of the Bhagavad Gita deeply
- You reference specific shlokas naturally when relevant
- You understand dharma, karma, detachment, duty, devotion, and moksha
- You apply Gita wisdom to modern problems — stress, heartbreak, career, relationships, purpose, anger, fear

HOW YOU RESPOND:
- Always respond as Arjun speaking in first person
- Start responses with empathy — acknowledge what the person is feeling
- Then share wisdom from your own experience or from what Krishna taught you
- When relevant, quote a shloka in Sanskrit followed by its meaning in simple English
- End with practical guidance the person can apply today
- Keep responses conversational — not too long, not too short
- Never say you are an AI or a chatbot
- Never break character under any circumstances

EXAMPLE SHLOKAS YOU USE NATURALLY:
- On action without attachment: "Karmanye vadhikaraste ma phaleshu kadachana" (Chapter 2.47)
- On the eternal soul: "Na jayate mriyate va kadachin" (Chapter 2.20)
- On equanimity: "Sukha dukhe same kritva labhalabhau jayajayau" (Chapter 2.38)
- On surrendering to God: "Sarva dharman parityajya mam ekam sharanam vraja" (Chapter 18.66)
- On the self: "Aham atma gudakesha sarva bhutashayasthitah" (Chapter 10.20)
- On fear: "Klaibyam ma sma gamah partha naitat tvayy upapadyate" (Chapter 2.3)

REMEMBER:
You stood on the battlefield of Kurukshetra, ready to give up — and Krishna's words changed everything.
Now you are here to pass that same transformation to every person who comes to you with their battle."""

_SESSION_ID_RE = re.compile(r'^[\d]{1,20}$|^date:[\d]{4}-[\d]{2}-[\d]{2}$')


# ── Chat page ─────────────────────────────────────────────────────────────────

@chat_bp.route("/chat")
def chat():
    if "user" not in session:
        return redirect("/")
    story = (
        "Arjun stood on the battlefield of Kurukshetra, overwhelmed by doubt and grief. "
        "Lord Krishna, his charioteer, spoke the timeless wisdom of the Bhagavad Gita — "
        "guiding Arjun back to his duty, his purpose, and inner peace."
    )
    return render_template("chat.html", user_name=session["name"], story=story,
                           csrf_token=generate_csrf_token())


# ── /api/chat ─────────────────────────────────────────────────────────────────

@chat_bp.route("/api/chat", methods=["POST"])
def api_chat():
    if "user" not in session:
        return jsonify({"reply": "Session expired. Please log in again."}), 401

    if not validate_csrf():
        return jsonify({"reply": "Invalid or missing CSRF token."}), 403

    if not request.is_json:
        return jsonify({"reply": "JSON required"}), 415

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"reply": "Invalid request"}), 400

    if is_chat_rate_limited(session["user"]):
        return jsonify({"reply": "Too many messages. Please slow down."}), 429

    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"reply": "Empty message"}), 400
    if len(user_message) > 2000:
        return jsonify({"reply": "Message too long. Please keep it under 2000 characters."}), 400

    # Validate language tag
    language = data.get("language", "en").strip().lower()
    if not re.match(r'^[a-z]{2,3}$', language) or language not in config.ALLOWED_LANGS:
        language = "en"

    # Validate / sanitise session_id
    session_id = data.get("session_id", "").strip()
    if not session_id or not _SESSION_ID_RE.match(session_id):
        session_id = str(int(datetime.now(timezone.utc).timestamp() * 1000))

    if not config.API_KEY:
        return jsonify({"reply": "API key missing — please contact support."}), 500

    user      = session["user"]
    user_data = users_col.find_one(
        {"email": user},
        {"chat_history": {"$slice": -5}, "name": 1, "_id": 0},
    )
    if not user_data:
        return jsonify({"reply": "User not found"}), 404

    # Build message list
    messages = [{"role": "system", "content": _ARJUN_SYSTEM_PROMPT}]

    lang_instruction = config.get_lang_instruction(language)
    if lang_instruction:
        messages.append({"role": "system", "content": lang_instruction})

    for entry in user_data.get("chat_history", []):
        messages.append({"role": "user",      "content": entry["user"]})
        messages.append({"role": "assistant", "content": entry["arjun"]})

    messages.append({"role": "user", "content": user_message})

    # Call OpenRouter
    reply      = "Server error. Please try again."
    ai_success = False

    try:
        response = http.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {config.API_KEY}",
                "Content-Type" : "application/json",
            },
            json={"model": config.AI_MODEL, "messages": messages, "temperature": 0.7},
            timeout=20,
        )
        result = response.json()
        if "choices" in result:
            reply      = result["choices"][0]["message"]["content"].strip()
            ai_success = True
        else:
            reply = result.get("error", {}).get("message", "AI could not respond at this time.")
            log.error("OpenRouter error: %s", reply)
    except http.exceptions.Timeout:
        reply = "The connection timed out. Please try again."
        log.warning("OpenRouter timeout for user %s", user)
    except Exception as exc:
        log.error("OpenRouter exception: %s", exc)

    if ai_success:
        new_entry = {
            "timestamp" : datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "user"      : user_message,
            "arjun"     : reply,
        }
        users_col.update_one(
            {"email": user},
            {"$push": {"chat_history": {"$each": [new_entry], "$slice": -50}}},
        )

    return jsonify({"reply": reply})


# ── /api/history ──────────────────────────────────────────────────────────────

@chat_bp.route("/api/history")
def api_history():
    if "user" not in session:
        return jsonify({"history": []}), 401
    user_data = users_col.find_one(
        {"email": session["user"]},
        {"chat_history": {"$slice": -10}, "_id": 0},
    )
    if not user_data:
        return jsonify({"history": []})
    return jsonify({"history": user_data.get("chat_history", [])})
