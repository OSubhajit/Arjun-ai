from flask import Flask, render_template, request, jsonify, session, redirect
from markupsafe import escape as html_escape
from collections import OrderedDict
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import os
import re
import secrets
import hmac
import requests
import bcrypt
import traceback
import sys

load_dotenv()

API_KEY    = os.getenv("OPENROUTER_API_KEY")
MONGO_URI  = os.getenv("MONGO_URI")
SECRET_KEY = os.getenv("SECRET_KEY")
IS_PROD    = os.getenv("RENDER") == "true"
AI_MODEL   = os.getenv("AI_MODEL", "openai/gpt-3.5-turbo")

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
rate_collection  = db["rate_limits"]

# FIX 06 — unique index on email prevents duplicate accounts from race conditions
try:
    users_collection.create_index("email", unique=True, background=True)
    print("✅ Unique email index ready")
except Exception as e:
    print("⚠️  Email index warning:", e)

try:
    otp_collection.create_index(
        [("expires_at", ASCENDING)], expireAfterSeconds=0, background=True
    )
    print("✅ OTP TTL index ready")
except Exception as e:
    print("⚠️  OTP TTL index warning:", e)

try:
    rate_collection.create_index(
        [("expires_at", ASCENDING)], expireAfterSeconds=0, background=True
    )
    print("✅ Rate limit TTL index ready")
except Exception as e:
    print("⚠️  Rate limit TTL index warning:", e)

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['SESSION_COOKIE_SECURE']      = IS_PROD
app.config['SESSION_COOKIE_HTTPONLY']    = True
app.config['SESSION_COOKIE_SAMESITE']   = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)


# FIX 04 — Security headers on every response
@app.after_request
def set_security_headers(response):
    response.headers['X-Frame-Options']        = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy']        = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://pagead2.googlesyndication.com "
        "https://partner.googleadservices.com https://tpc.googlesyndication.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self'; "
        "frame-src https://googleads.g.doubleclick.net https://tpc.googlesyndication.com;"
    )
    return response


_EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')

def is_valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email))


def is_rate_limited(ip: str, max_calls: int = 3, window_sec: int = 600) -> bool:
    """OTP rate limiter — 3 sends per 10 minutes per IP."""
    now          = datetime.now(timezone.utc)
    window_start = now - timedelta(seconds=window_sec)
    count = rate_collection.count_documents({"ip": ip, "created_at": {"$gte": window_start}})
    if count >= max_calls:
        return True
    rate_collection.insert_one({
        "ip": ip, "created_at": now,
        "expires_at": now + timedelta(seconds=window_sec)
    })
    return False


# FIX 01 — Login brute-force protection (separate key-space)
def is_login_rate_limited(ip: str) -> bool:
    """Max 10 login attempts per 15 minutes per IP."""
    now          = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=15)
    key = f"login:{ip}"
    count = rate_collection.count_documents({"ip": key, "created_at": {"$gte": window_start}})
    if count >= 10:
        return True
    rate_collection.insert_one({
        "ip": key, "created_at": now,
        "expires_at": now + timedelta(minutes=15)
    })
    return False


def generate_csrf_token() -> str:
    """Generate and store a CSRF token in the session."""
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    return session['csrf_token']


def validate_csrf() -> bool:
    """Validate CSRF token from X-CSRF-Token header against session value."""
    token = request.headers.get('X-CSRF-Token', '')
    stored = session.get('csrf_token', '')
    if not token or not stored:
        return False
    return hmac.compare_digest(token, stored)


def verify_otp_value(stored: str, provided: str) -> bool:
    """Constant-time comparison — prevents timing-based OTP brute-force."""
    if not stored or not provided:
        return False
    return hmac.compare_digest(str(stored), str(provided))


def is_chat_rate_limited(email: str, max_calls: int = 20, window_sec: int = 60) -> bool:
    """Chat rate limiter — 20 messages per minute per user."""
    now          = datetime.now(timezone.utc)
    window_start = now - timedelta(seconds=window_sec)
    key = f"chat:{email}"
    count = rate_collection.count_documents({"ip": key, "created_at": {"$gte": window_start}})
    if count >= max_calls:
        return True
    rate_collection.insert_one({
        "ip": key, "created_at": now,
        "expires_at": now + timedelta(seconds=window_sec)
    })
    return False


def sanitize_name(name: str) -> str:
    """Strip HTML tags and limit length on display names."""
    name = str(html_escape(name.strip()))
    return name[:100]



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
        print(f"❌ Script error: {result.get('error')}")
        return False
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False


def otp_save(email: str, data: dict):
    data["email"]      = email
    data["expires_at"] = datetime.now(timezone.utc) + timedelta(minutes=10)
    data.setdefault("attempts", 0)   # FIX 05 — track verify attempts
    otp_collection.replace_one({"email": email}, data, upsert=True)


def otp_get(email: str):
    doc = otp_collection.find_one({"email": email})
    if not doc:
        return None
    expires_at = doc["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires_at:
        otp_collection.delete_one({"email": email})
        return None
    return doc


def otp_delete(email: str):
    otp_collection.delete_one({"email": email})


# FIX 05 — Increment attempt counter; auto-lock after 5 failures
def otp_record_failed_attempt(email: str) -> int:
    result = otp_collection.find_one_and_update(
        {"email": email},
        {"$inc": {"attempts": 1}},
        return_document=True
    )
    return result["attempts"] if result else 999


@app.route('/')
def index():
    if 'user' in session:
        return redirect('/chat')
    return redirect('/login')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html', csrf_token=generate_csrf_token())

    if not validate_csrf():
        return jsonify({"success": False, "message": "Invalid or missing CSRF token."}), 403

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Invalid request"})

    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')
    remember = bool(data.get('rememberMe', False))   # FIX 08

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password required"})

    if not is_valid_email(email):
        return jsonify({"success": False, "message": "Invalid email address"})

    # FIX 01 — brute-force protection
    ip = request.remote_addr or "unknown"
    if is_login_rate_limited(ip):
        return jsonify({"success": False, "message": "Too many login attempts. Please wait 15 minutes."})

    user = users_collection.find_one({"email": email})

    if not user or not bcrypt.checkpw(password.encode(), user['password'].encode()):
        return jsonify({"success": False, "message": "Invalid credentials"})

    # FIX 02 — clear before set prevents session fixation
    session.clear()
    session.permanent = remember   # FIX 08
    session['user']   = email
    session['name']   = user['name']
    return jsonify({"success": True, "redirect": "/chat"})


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html', csrf_token=generate_csrf_token())

    if not validate_csrf():
        return jsonify({"success": False, "message": "Invalid or missing CSRF token."}), 403

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Invalid request"})

    action = data.get("action")
    email  = data.get('email', '').strip().lower()

    if not email or not action:
        return jsonify({"success": False, "message": "Email and action required"})

    if not is_valid_email(email):
        return jsonify({"success": False, "message": "Invalid email address"})

    if action == "send_otp":
        name     = sanitize_name(data.get('name', ''))
        password = data.get('password', '')

        if not name or not password:
            return jsonify({"success": False, "message": "All fields required"})

        if len(password) < 8:
            return jsonify({"success": False, "message": "Password must be at least 8 characters"})

        ip = request.remote_addr or "unknown"
        if is_rate_limited(ip):
            return jsonify({"success": False, "message": "Too many OTP requests. Please wait 10 minutes."})

        try:
            if users_collection.find_one({"email": email}):
                return jsonify({"success": False, "message": "User already exists"})
        except Exception as e:
            print("DB error:", e)
            return jsonify({"success": False, "message": "Database error. Please try again."})

        otp             = str(secrets.randbelow(900000) + 100000)
        hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        otp_save(email, {
            "otp": otp, "name": name,
            "password": hashed_password, "type": "register"
        })

        sent = send_email_otp(email, otp, name=name)
        if not sent:
            otp_delete(email)   # FIX — clean up stored OTP if send fails
            return jsonify({"success": False, "message": "Failed to send OTP. Check GMAIL_SCRIPT_URL."})

        return jsonify({"success": True, "message": "OTP sent to your email!"})

    elif action == "verify_otp":
        user_data = otp_get(email)

        if not user_data:
            return jsonify({"success": False, "message": "OTP not found or expired. Please request a new one."})

        if user_data.get("type") != "register":
            return jsonify({"success": False, "message": "Invalid OTP type."})

        # FIX 05 — block after 5 failed attempts
        if user_data.get("attempts", 0) >= 5:
            otp_delete(email)
            return jsonify({"success": False, "message": "Too many failed attempts. Please request a new OTP."})

        if not verify_otp_value(user_data["otp"], data.get("otp", "")):
            attempts  = otp_record_failed_attempt(email)
            remaining = max(0, 5 - attempts)
            return jsonify({"success": False, "message": f"Invalid OTP. {remaining} attempt(s) remaining."})

        try:
            users_collection.insert_one({
                "email"       : email,
                "name"        : user_data["name"],
                "password"    : user_data["password"],
                "chat_history": [],
                "notes"       : []
            })
        except DuplicateKeyError:
            # FIX 06 — unique index caught race condition duplicate
            otp_delete(email)
            return jsonify({"success": False, "message": "User already exists. Please log in."})
        except Exception as e:
            print("DB error:", e)
            return jsonify({"success": False, "message": "Database error. Please try again."})

        otp_delete(email)
        session.clear()   # FIX 02
        session.permanent = True
        session['user']   = email
        session['name']   = user_data["name"]
        return jsonify({"success": True, "redirect": "/chat"})

    return jsonify({"success": False, "message": "Invalid action"})


@app.route('/chat')
def chat():
    if 'user' not in session:
        return redirect('/')
    story = ("Arjun stood on the battlefield of Kurukshetra, overwhelmed by doubt and grief. "
             "Lord Krishna, his charioteer, spoke the timeless wisdom of the Bhagavad Gita — "
             "guiding Arjun back to his duty, his purpose, and inner peace.")
    return render_template('chat.html', user_name=session['name'], story=story, csrf_token=generate_csrf_token())


@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'GET':
        return render_template('forgot.html', csrf_token=generate_csrf_token())

    if not validate_csrf():
        return jsonify({"success": False, "message": "Invalid or missing CSRF token."}), 403

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

        user = users_collection.find_one({"email": email})
        if user:
            otp = str(secrets.randbelow(900000) + 100000)
            otp_save(email, {"otp": otp, "name": user.get("name", "User"), "type": "forgot"})
            send_email_otp(email, otp, name=user.get("name", "User"))

        return jsonify({
            "success": True,
            "message": "If this email is registered, you'll receive an OTP shortly."
        })

    if action == "reset_password":
        otp          = data.get("otp", "")
        new_password = data.get("password", "")

        if not new_password:
            return jsonify({"success": False, "message": "New password is required"})
        if len(new_password) < 8:
            return jsonify({"success": False, "message": "Password must be at least 8 characters"})

        user_data = otp_get(email)

        # FIX 05 — attempt limit on forgot-password OTP too
        if user_data and user_data.get("attempts", 0) >= 5:
            otp_delete(email)
            return jsonify({"success": False, "message": "Too many failed attempts. Please request a new OTP."})

        if not user_data or not verify_otp_value(user_data.get("otp", ""), otp):
            if user_data:
                attempts  = otp_record_failed_attempt(email)
                remaining = max(0, 5 - attempts)
                return jsonify({"success": False, "message": f"Invalid OTP. {remaining} attempt(s) remaining."})
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

    if not validate_csrf():
        return jsonify({'reply': 'Invalid or missing CSRF token.'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'reply': 'Invalid request'}), 400

    # Chat rate limit — 20 messages per minute per user
    if is_chat_rate_limited(session['user']):
        return jsonify({'reply': 'Too many messages. Please slow down.'}), 429

    user_message = data.get("message", "").strip()
    language     = data.get("language", "en").strip()
    ALLOWED_LANGS = {"en","hi","bn","ta","te","mr","es","fr","de","ja"}
    if language not in ALLOWED_LANGS:
        language = "en"
    session_id   = data.get("session_id", "").strip() or str(int(datetime.now(timezone.utc).timestamp() * 1000))
    # Validate session_id: digits only (ms timestamp) or date:-prefixed legacy format, max 30 chars
    if not re.match(r'^[\d]{1,20}$|^date:[\d]{4}-[\d]{2}-[\d]{2}$', session_id):
        session_id = str(int(datetime.now(timezone.utc).timestamp() * 1000))
    if not user_message:
        return jsonify({'reply': 'Empty message'}), 400

    if len(user_message) > 2000:
        return jsonify({'reply': 'Message too long. Please keep it under 2000 characters.'}), 400

    if not API_KEY:
        return jsonify({'reply': 'API key missing — please contact support.'}), 500

    user      = session['user']
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

    LANG_INSTRUCTIONS = {
        "hi": "IMPORTANT: Respond entirely in Hindi. Keep Sanskrit shlokas in Sanskrit but give their meaning in Hindi.",
        "bn": "IMPORTANT: Respond entirely in Bengali. Keep Sanskrit shlokas in Sanskrit but give their meaning in Bengali.",
        "ta": "IMPORTANT: Respond entirely in Tamil. Keep Sanskrit shlokas in Sanskrit but give their meaning in Tamil.",
        "te": "IMPORTANT: Respond entirely in Telugu. Keep Sanskrit shlokas in Sanskrit but give their meaning in Telugu.",
        "mr": "IMPORTANT: Respond entirely in Marathi. Keep Sanskrit shlokas in Sanskrit but give their meaning in Marathi.",
        "es": "IMPORTANT: Respond entirely in Spanish. Keep Sanskrit shlokas in Sanskrit but give their meaning in Spanish.",
        "fr": "IMPORTANT: Respond entirely in French. Keep Sanskrit shlokas in Sanskrit but give their meaning in French.",
        "de": "IMPORTANT: Respond entirely in German. Keep Sanskrit shlokas in Sanskrit but give their meaning in German.",
        "ja": "IMPORTANT: Respond entirely in Japanese. Keep Sanskrit shlokas in Sanskrit but give their meaning in Japanese.",
    }
    if language in LANG_INSTRUCTIONS:
        messages.append({"role": "system", "content": LANG_INSTRUCTIONS[language]})

    for chat_entry in history:
        messages.append({"role": "user",      "content": chat_entry["user"]})
        messages.append({"role": "assistant", "content": chat_entry["arjun"]})

    messages.append({"role": "user", "content": user_message})

    ai_success = False
    reply      = "Server error. Please try again."

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": AI_MODEL, "messages": messages, "temperature": 0.7},
            timeout=20
        )
        result = response.json()
        if "choices" in result:
            reply      = result["choices"][0]["message"]["content"].strip()
            ai_success = True
        else:
            reply = result.get("error", {}).get("message", "AI could not respond at this time.")
    except requests.exceptions.Timeout:
        reply = "The connection timed out. Please try again."
    except Exception as e:
        print("AI ERROR:", e)

    # FIX 07 — only persist successful AI responses; never store error strings
    if ai_success:
        new_entry = {
            "timestamp" : datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "user"      : user_message,
            "arjun"     : reply
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
    return render_template('profile.html', csrf_token=generate_csrf_token())


@app.route('/api/profile')
def api_profile():
    if 'user' not in session:
        return jsonify({"error": "Not logged in"}), 401

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

    if not validate_csrf():
        return jsonify({"error": "Invalid or missing CSRF token."}), 403

    # Accept: numeric session_id (ms timestamp), date: prefix, or legacy YYYY-MM-DD
    is_date_only   = bool(re.match(r'^\d{4}-\d{2}-\d{2}$', date))
    is_session_id  = bool(re.match(r'^\d+$', date))
    is_date_prefix = date.startswith("date:")
    if not (is_date_only or is_session_id or is_date_prefix):
        return jsonify({"error": "Invalid session identifier"}), 400

    # FIX — use $pull (server-side) instead of fetch-filter-rewrite (Python-side)
    if is_session_id:
        pull_filter = {"session_id": date}
    elif is_date_prefix:
        date_val = date[5:]
        # Legacy entries: no session_id AND timestamp starts with date_val
        pull_filter = {"session_id": {"$exists": False}, "timestamp": {"$regex": f"^{re.escape(date_val)}"}}
    else:
        pull_filter = {"timestamp": {"$regex": f"^{re.escape(date)}"}}

    result = users_collection.update_one(
        {"email": session['user']},
        {"$pull": {"chat_history": pull_filter}}
    )
    if result.matched_count == 0:
        return jsonify({"error": "User not found"}), 404

    return jsonify({"success": True, "deleted_session": date})


@app.route('/api/history')
def api_history():
    if 'user' not in session:
        return jsonify({"history": []}), 401
    user_data = users_collection.find_one(
        {"email": session['user']},
        {"chat_history": {"$slice": -10}, "_id": 0}
    )
    if not user_data:
        return jsonify({"history": []})
    return jsonify({"history": user_data.get("chat_history", [])})


def _group_by_session(history):
    """Group chat_history entries by session_id.
    Old entries without session_id are grouped by date (backward compat).
    Returns list of {session_id, label, date, messages} dicts."""
    groups = OrderedDict()
    for entry in history:
        ts         = entry.get("timestamp", "")
        session_id = entry.get("session_id") or ("date:" + (ts[:10] if ts else "unknown"))
        if session_id not in groups:
            groups[session_id] = {
                "session_id": session_id,
                "label"     : _session_label(ts),
                "date"      : ts[:10] if ts else "Unknown",
                "messages"  : []
            }
        groups[session_id]["messages"].append({
            "user"     : entry.get("user", ""),
            "arjun"    : entry.get("arjun", ""),
            "timestamp": ts
        })
    return list(groups.values())


def _session_label(ts: str) -> str:
    """Convert ISO timestamp to human-readable session label."""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y · %I:%M %p").lstrip("0")
    except Exception:
        return ts[:16] if ts else "Unknown"


# Keep _group_by_date as alias for backward compat with profile page
def _group_by_date(history):
    return _group_by_session(history)


@app.route('/api/csrf-token')
def csrf_token_endpoint():
    """Returns a CSRF token. JS fetches this once and attaches X-CSRF-Token header."""
    return jsonify({"csrf_token": generate_csrf_token()})


@app.route('/privacy')
def privacy():
    return render_template('privacy.html')


# FIX 03 — POST-only logout prevents CSRF logout attacks via <img> or link injection
@app.route('/logout', methods=['POST'])
def logout():
    if not validate_csrf():
        return jsonify({"success": False, "message": "Invalid or missing CSRF token."}), 403
    session.clear()
    return jsonify({"success": True, "redirect": "/"})


if __name__ == "__main__":
    try:
        port = int(os.environ.get("PORT", 5000))
        print(f"✅ Starting app on port {port}")
        app.run(host="0.0.0.0", port=port, debug=not IS_PROD)
    except Exception as e:
        print("❌ STARTUP ERROR:", e)
        traceback.print_exc()
        sys.exit(1)
