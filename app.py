from flask import Flask, render_template, request, jsonify, session, redirect
import os
import secrets          # FIX 06 — replaces random module for OTP generation
import hmac             # FIX 10 — constant-time OTP comparison
import re               # FIX 17 — backend email validation
import requests
from datetime import datetime, timedelta, timezone   # FIX 12 — timezone-aware datetimes
from pymongo import MongoClient, ASCENDING
from dotenv import load_dotenv
import bcrypt
import traceback
import sys

# ================= ENV =================
load_dotenv()

API_KEY    = os.getenv("OPENROUTER_API_KEY")
MONGO_URI  = os.getenv("MONGO_URI")
SECRET_KEY = os.getenv("SECRET_KEY")
IS_PROD    = os.getenv("RENDER") == "true"
AI_MODEL   = os.getenv("AI_MODEL", "openai/gpt-3.5-turbo")   # FIX 18 — model from env var

# FIX 02 — Never allow a missing or guessable SECRET_KEY in production
if not SECRET_KEY:
    if IS_PROD:
        print("❌ SECRET_KEY env var not set — refusing to start in production")
        sys.exit(1)
    else:
        SECRET_KEY = "dev_only_not_for_production"
        print("⚠️  WARNING: Using dev SECRET_KEY. Set SECRET_KEY env var before deploying.")

print("=== STARTUP ===")
print("MONGO_URI:", "set" if MONGO_URI else "MISSING")
print("API_KEY  :", "set" if API_KEY else "MISSING")
print("AI_MODEL :", AI_MODEL)
print("IS_PROD  :", IS_PROD)
print("===============")

if not MONGO_URI:
    print("❌ MONGO_URI not found — exiting")
    sys.exit(1)

# ================= MONGODB =================
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.server_info()
    print("✅ MongoDB Connected")
except Exception as e:
    print("❌ MongoDB Error:", e)
    traceback.print_exc()
    sys.exit(1)

db               = client["OSubhajit"]
users_collection = db["users"]
otp_collection   = db["otp_store"]
# FIX 07 — dedicated collection for rate limiting so it works across all Gunicorn workers
rate_collection  = db["rate_limits"]

# OTP TTL index — MongoDB auto-deletes expired OTPs
try:
    otp_collection.create_index(
        [("expires_at", ASCENDING)],
        expireAfterSeconds=0,
        background=True
    )
    print("✅ OTP TTL index ready")
except Exception as e:
    print("⚠️  OTP TTL index warning:", e)

# FIX 07 — Rate limit TTL index — auto-cleans old entries; no memory leak
try:
    rate_collection.create_index(
        [("expires_at", ASCENDING)],
        expireAfterSeconds=0,
        background=True
    )
    print("✅ Rate limit TTL index ready")
except Exception as e:
    print("⚠️  Rate limit TTL index warning:", e)

# ================= APP =================
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['SESSION_COOKIE_SECURE']      = IS_PROD
app.config['SESSION_COOKIE_HTTPONLY']    = True
app.config['SESSION_COOKIE_SAMESITE']   = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# ================= HELPERS =================

# FIX 17 — backend email format validation (compiled once at startup)
_EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')

def is_valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email))


def is_rate_limited(ip: str, max_calls: int = 3, window_sec: int = 600) -> bool:
    """
    FIX 07 — MongoDB-backed distributed rate limiter.
    Works correctly across multiple Gunicorn workers on Render.
    FIX 16 — No memory leak: TTL index auto-purges old entries from the DB.
    """
    now          = datetime.now(timezone.utc)
    window_start = now - timedelta(seconds=window_sec)

    count = rate_collection.count_documents({
        "ip"        : ip,
        "created_at": {"$gte": window_start}
    })
    if count >= max_calls:
        return True

    rate_collection.insert_one({
        "ip"        : ip,
        "created_at": now,
        "expires_at": now + timedelta(seconds=window_sec)  # TTL index cleans this up
    })
    return False


def verify_otp_value(stored: str, provided: str) -> bool:
    """FIX 10 — constant-time comparison prevents timing-based OTP brute-force."""
    if not stored or not provided:
        return False
    return hmac.compare_digest(str(stored), str(provided))

# ================= EMAIL =================
def send_email_otp(email, otp, name="User"):
    script_url = os.getenv("GMAIL_SCRIPT_URL")
    if not script_url:
        print("❌ GMAIL_SCRIPT_URL not set")
        return False
    try:
        response = requests.post(
            script_url,
            json={"to": email, "name": name, "otp": otp},
            timeout=15
        )
        result = response.json()
        if result.get("success"):
            print(f"✅ OTP sent to {email}")
            return True
        else:
            print(f"❌ Script error: {result.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False

# ================= OTP HELPERS =================
def otp_save(email: str, data: dict):
    data["email"]      = email
    data["expires_at"] = datetime.now(timezone.utc) + timedelta(minutes=10)  # FIX 12
    otp_collection.replace_one({"email": email}, data, upsert=True)


def otp_get(email: str):
    doc = otp_collection.find_one({"email": email})
    if not doc:
        return None
    expires_at = doc["expires_at"]
    # Normalise: MongoDB stores naive UTC datetimes; make timezone-aware for comparison
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires_at:
        otp_collection.delete_one({"email": email})
        return None
    return doc


def otp_delete(email: str):
    otp_collection.delete_one({"email": email})

# ================= ROUTES =================

@app.route('/')
def index():
    if 'user' in session:
        return redirect('/chat')
    return redirect('/login')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Invalid request"})

    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password required"})

    # FIX 17 — validate email format on backend too
    if not is_valid_email(email):
        return jsonify({"success": False, "message": "Invalid email address"})

    user = users_collection.find_one({"email": email})

    if not user or not bcrypt.checkpw(password.encode(), user['password'].encode()):
        return jsonify({"success": False, "message": "Invalid credentials"})

    session.permanent = True
    session['user']   = email
    session['name']   = user['name']
    return jsonify({"success": True, "redirect": "/chat"})


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('login.html')

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Invalid request"})

    action = data.get("action")
    email  = data.get('email', '').strip().lower()

    if not email or not action:
        return jsonify({"success": False, "message": "Email and action required"})

    # FIX 17 — backend email validation
    if not is_valid_email(email):
        return jsonify({"success": False, "message": "Invalid email address"})

    if action == "send_otp":
        name     = data.get('name', '').strip()
        password = data.get('password', '')

        if not name or not password:
            return jsonify({"success": False, "message": "All fields required"})

        # FIX 08 — server-side password length enforcement
        if len(password) < 8:
            return jsonify({"success": False, "message": "Password must be at least 8 characters"})

        # FIX 07 — MongoDB-backed rate limiter
        ip = request.remote_addr or "unknown"
        if is_rate_limited(ip):
            return jsonify({"success": False, "message": "Too many OTP requests. Please wait 10 minutes."})

        try:
            if users_collection.find_one({"email": email}):
                return jsonify({"success": False, "message": "User already exists"})
        except Exception as e:
            print("DB error:", e)
            return jsonify({"success": False, "message": "Database error. Please try again."})

        # FIX 06 — cryptographically secure 6-digit OTP
        otp = str(secrets.randbelow(900000) + 100000)

        # FIX 01 — hash password BEFORE storing in OTP collection; never store plaintext
        hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        otp_save(email, {
            "otp"     : otp,
            "name"    : name,
            "password": hashed_password,   # stored as bcrypt hash, not plaintext
            "type"    : "register"
        })

        sent = send_email_otp(email, otp, name=name)
        if not sent:
            return jsonify({"success": False, "message": "Failed to send OTP. Check GMAIL_SCRIPT_URL."})

        return jsonify({"success": True, "message": "OTP sent to your email!"})

    elif action == "verify_otp":
        user_data = otp_get(email)

        if not user_data:
            return jsonify({"success": False, "message": "OTP not found or expired. Please request a new one."})

        if user_data.get("type") != "register":
            return jsonify({"success": False, "message": "Invalid OTP type."})

        # FIX 10 — constant-time comparison
        if not verify_otp_value(user_data["otp"], data.get("otp", "")):
            return jsonify({"success": False, "message": "Invalid OTP"})

        try:
            if users_collection.find_one({"email": email}):
                return jsonify({"success": False, "message": "User already exists"})

            # FIX 01 — password is already bcrypt-hashed; insert directly, no double-hashing
            users_collection.insert_one({
                "email"       : email,
                "name"        : user_data["name"],
                "password"    : user_data["password"],
                "chat_history": [],
                "notes"       : []
            })
        except Exception as e:
            print("DB error:", e)
            return jsonify({"success": False, "message": "Database error. Please try again."})

        otp_delete(email)
        session.permanent = True
        session['user']   = email
        session['name']   = user_data["name"]
        return jsonify({"success": True, "redirect": "/chat"})

    return jsonify({"success": False, "message": "Invalid action"})


@app.route('/chat')
def chat():
    if 'user' not in session:
        return redirect('/')
    story = "Arjun stood on the battlefield of Kurukshetra, overwhelmed by doubt and grief. Lord Krishna, his charioteer, spoke the timeless wisdom of the Bhagavad Gita — guiding Arjun back to his duty, his purpose, and inner peace."
    return render_template('chat.html', user_name=session['name'], story=story)


@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'GET':
        return render_template('forgot.html')

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Invalid request"})

    action = data.get("action")
    email  = data.get("email", "").strip().lower()

    if not email or not is_valid_email(email):
        return jsonify({"success": False, "message": "Valid email is required"})

    if action == "send_otp":
        ip = request.remote_addr or "unknown"
        if is_rate_limited(ip):
            return jsonify({"success": False, "message": "Too many OTP requests. Please wait 10 minutes."})

        # FIX 05 — look up user silently; never reveal whether email is registered
        user = users_collection.find_one({"email": email})
        if user:
            otp = str(secrets.randbelow(900000) + 100000)   # FIX 06
            otp_save(email, {"otp": otp, "name": user.get("name", "User"), "type": "forgot"})
            send_email_otp(email, otp, name=user.get("name", "User"))

        # FIX 05 — identical response whether email exists or not
        return jsonify({
            "success": True,
            "message": "If this email is registered, you'll receive an OTP shortly."
        })

    if action == "reset_password":
        otp          = data.get("otp", "")
        new_password = data.get("password", "")

        # FIX 09 — validate before touching new_password to prevent AttributeError crash
        if not new_password:
            return jsonify({"success": False, "message": "New password is required"})
        if len(new_password) < 8:
            return jsonify({"success": False, "message": "Password must be at least 8 characters"})

        user_data = otp_get(email)
        # FIX 10 — constant-time comparison
        if not user_data or not verify_otp_value(user_data.get("otp", ""), otp):
            return jsonify({"success": False, "message": "Invalid or expired OTP"})
        if user_data.get("type") != "forgot":
            return jsonify({"success": False, "message": "Invalid OTP type"})

        hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        users_collection.update_one({"email": email}, {"$set": {"password": hashed}})
        otp_delete(email)
        return jsonify({"success": True})

    return jsonify({"success": False, "message": "Invalid action"})


@app.route('/help')
def help_page():
    return render_template('help.html')


@app.route('/api/chat', methods=['POST'])
def api_chat():
    if 'user' not in session:
        return jsonify({'reply': 'Session expired. Please log in again.'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'reply': 'Invalid request'}), 400

    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({'reply': 'Empty message'}), 400

    # FIX 11 — hard limit on message length to prevent API abuse and cost explosion
    if len(user_message) > 2000:
        return jsonify({'reply': 'Message too long. Please keep it under 2000 characters.'}), 400

    if not API_KEY:
        return jsonify({'reply': 'API key missing — please contact support.'}), 500

    user = session['user']

    # FIX 14 — projection: fetch only the last 5 chat turns + name; skip the rest of the document
    user_data = users_collection.find_one(
        {"email": user},
        {"chat_history": {"$slice": -5}, "name": 1, "_id": 0}
    )
    if not user_data:
        return jsonify({'reply': 'User not found'}), 404

    history  = user_data.get("chat_history", [])
    messages = [{"role": "system", "content": """You are Arjun — the legendary warrior of Kurukshetra from the Mahabharata.

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
- On action without attachment: \"Karmanye vadhikaraste ma phaleshu kadachana\" (Chapter 2.47)
- On the eternal soul: \"Na jayate mriyate va kadachin\" (Chapter 2.20)
- On equanimity: \"Sukha dukhe same kritva labhalabhau jayajayau\" (Chapter 2.38)
- On surrendering to God: \"Sarva dharman parityajya mam ekam sharanam vraja\" (Chapter 18.66)
- On the self: \"Aham atma gudakesha sarva bhutashayasthitah\" (Chapter 10.20)
- On fear: \"Klaibyam ma sma gamah partha naitat tvayy upapadyate\" (Chapter 2.3)

REMEMBER:
You stood on the battlefield of Kurukshetra, ready to give up — and Krishna's words changed everything.
Now you are here to pass that same transformation to every person who comes to you with their battle."""}]

    for chat_entry in history:
        messages.append({"role": "user",      "content": chat_entry["user"]})
        messages.append({"role": "assistant", "content": chat_entry["arjun"]})

    messages.append({"role": "user", "content": user_message})

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type" : "application/json"
            },
            json={
                "model"      : AI_MODEL,    # FIX 18 — from env var, not hardcoded
                "messages"   : messages,
                "temperature": 0.7
            },
            timeout=20
        )
        result = response.json()
        if "choices" in result:
            reply = result["choices"][0]["message"]["content"].strip()
        else:
            reply = result.get("error", {}).get("message", "AI could not respond at this time.")
    except requests.exceptions.Timeout:
        reply = "The connection timed out. Please try again."
    except Exception as e:
        print("AI ERROR:", e)
        reply = "Server error. Please try again."

    # FIX 13 — UTC ISO 8601 timestamp; consistent, parseable, timezone-aware
    new_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user"     : user_message,
        "arjun"    : reply
    }

    users_collection.update_one(
        {"email": user},
        {"$push": {"chat_history": {"$each": [new_entry], "$slice": -50}}}
    )
    return jsonify({'reply': reply})


@app.route('/profile')
def profile():
    if 'user' not in session:
        return redirect('/')
    return render_template('profile.html')


@app.route('/api/profile')
def api_profile():
    if 'user' not in session:
        return jsonify({"error": "Not logged in"}), 401

    # FIX 14 — projection: only fetch the fields this route actually uses
    user_data = users_collection.find_one(
        {"email": session['user']},
        {"name": 1, "email": 1, "chat_history": 1, "_id": 0}
    )
    if not user_data:
        return jsonify({"error": "User not found"}), 404

    history       = user_data.get("chat_history", [])
    conversations = _group_by_date(history)

    return jsonify({
        "name"           : user_data.get("name", ""),
        "email"          : user_data.get("email", ""),
        "total_messages" : len(history),
        "total_sessions" : len(conversations),
        "conversations"  : conversations
    })


@app.route('/api/conversations')
def api_conversations():
    if 'user' not in session:
        return jsonify({"conversations": []}), 401

    # FIX 14 — projection
    user_data = users_collection.find_one(
        {"email": session['user']},
        {"chat_history": 1, "_id": 0}
    )
    if not user_data:
        return jsonify({"conversations": []})
    history = user_data.get("chat_history", [])
    return jsonify({"conversations": _group_by_date(history)})


@app.route('/api/conversations/<date>', methods=['DELETE'])
def delete_conversation(date):
    if 'user' not in session:
        return jsonify({"error": "Not logged in"}), 401

    # Basic date format validation — must be YYYY-MM-DD
    import re
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
        return jsonify({"error": "Invalid date format"}), 400

    user_data = users_collection.find_one(
        {"email": session['user']},
        {"chat_history": 1, "_id": 0}
    )
    if not user_data:
        return jsonify({"error": "User not found"}), 404

    history     = user_data.get("chat_history", [])
    new_history = [
        e for e in history
        if not e.get("timestamp", "").startswith(date)
    ]

    users_collection.update_one(
        {"email": session['user']},
        {"$set": {"chat_history": new_history}}
    )
    return jsonify({"success": True, "deleted_date": date})


# FIX 04 — Restore the broken /api/history route (was orphaned dead code with no decorator)
@app.route('/api/history')
def api_history():
    if 'user' not in session:
        return jsonify({"history": []}), 401
    # FIX 14 — $slice projection fetches only last 10 entries; no full document load
    user_data = users_collection.find_one(
        {"email": session['user']},
        {"chat_history": {"$slice": -10}, "_id": 0}
    )
    if not user_data:
        return jsonify({"history": []})
    return jsonify({"history": user_data.get("chat_history", [])})


def _group_by_date(history):
    """Group flat chat_history list into date-keyed conversation sessions."""
    from collections import OrderedDict
    groups = OrderedDict()
    for entry in history:
        try:
            ts   = entry.get("timestamp", "")
            date = ts[:10] if ts else "Unknown"
        except Exception:
            date = "Unknown"
        if date not in groups:
            groups[date] = []
        groups[date].append({
            "user" : entry.get("user", ""),
            "arjun": entry.get("arjun", "")
        })
    return [{"date": d, "messages": msgs} for d, msgs in groups.items()]


@app.route('/privacy')
def privacy():
    return render_template('privacy.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# ================= RUN =================
if __name__ == "__main__":
    try:
        port = int(os.environ.get("PORT", 5000))
        print(f"✅ Starting app on port {port}")
        app.run(host="0.0.0.0", port=port, debug=not IS_PROD)
    except Exception as e:
        print("❌ STARTUP ERROR:", e)
        traceback.print_exc()
        sys.exit(1)