from flask import Flask, render_template, request, jsonify, session, redirect
import os
import random
import requests
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient, ASCENDING
from dotenv import load_dotenv
import bcrypt
import traceback
import sys
import time
from collections import defaultdict

# ================= ENV =================
load_dotenv()

API_KEY    = os.getenv("OPENROUTER_API_KEY")
MONGO_URI  = os.getenv("MONGO_URI")
SECRET_KEY = os.getenv("SECRET_KEY", "arjunai_secret_key_fixed_2024")
IS_PROD    = os.getenv("RENDER") == "true"   # Render sets RENDER=true automatically

print("=== STARTUP ===")
print("MONGO_URI:", "set" if MONGO_URI else "MISSING")
print("API_KEY  :", "set" if API_KEY else "MISSING")
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
otp_collection   = db["otp_store"]   # FIX 1 — OTPs in MongoDB (survives restarts)

# Create TTL index so MongoDB auto-deletes expired OTPs
try:
    otp_collection.create_index(
        [("expires_at", ASCENDING)],
        expireAfterSeconds=0,
        background=True
    )
    print("✅ OTP TTL index ready")
except Exception as e:
    print("⚠️  OTP TTL index warning:", e)

# ================= APP =================
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['SESSION_COOKIE_SECURE']      = IS_PROD   # FIX 2 — True on HTTPS, False locally
app.config['SESSION_COOKIE_HTTPONLY']    = True
app.config['SESSION_COOKIE_SAMESITE']   = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# ================= RATE LIMITER (FIX 6) =================
_rate_store = defaultdict(list)

def is_rate_limited(ip: str, max_calls: int = 3, window_sec: int = 600) -> bool:
    now   = time.time()
    calls = [t for t in _rate_store[ip] if now - t < window_sec]
    _rate_store[ip] = calls
    if len(calls) >= max_calls:
        return True
    _rate_store[ip].append(now)
    return False

# ================= EMAIL (Resend API — works on Render free tier) =================
def send_email_otp(email, otp, name="User"):
    api_key   = os.getenv("RESEND_API_KEY")
    from_addr = os.getenv("EMAIL_FROM", "onboarding@resend.dev")

    if not api_key:
        print("❌ RESEND_API_KEY not set")
        return False

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;background:#fff;border-radius:12px;overflow:hidden;">
      <div style="background:linear-gradient(135deg,#ff6b35,#f7931e);padding:30px;text-align:center;">
        <h1 style="color:white;margin:0;">🧠 GitaPath — Arjun AI</h1>
      </div>
      <div style="padding:30px;text-align:center;">
        <p>Hello <strong>{name}</strong>, your OTP is:</p>
        <div style="font-size:38px;font-weight:bold;color:#ff6b35;letter-spacing:8px;margin:20px 0;">{otp}</div>
        <p style="color:#999;font-size:13px;">Valid for 10 minutes. Do not share this OTP.</p>
      </div>
    </div>
    """

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type" : "application/json"
            },
            json={
                "from"   : f"Arjun AI <{from_addr}>",
                "to"     : [email],
                "subject": "🔐 Your OTP — GitaPath Arjun AI",
                "html"   : html
            },
            timeout=10
        )
        if response.status_code in (200, 201):
            print(f"✅ OTP sent to {email}")
            return True
        else:
            print(f"❌ Resend error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False

# ================= OTP HELPERS (FIX 1 & 3) =================
def otp_save(email: str, data: dict):
    data["email"]      = email
    data["expires_at"] = datetime.now(timezone.utc) + timedelta(minutes=10)
    otp_collection.replace_one({"email": email}, data, upsert=True)

def otp_get(email: str):
    doc = otp_collection.find_one({"email": email})
    if not doc:
        return None
    if datetime.now(timezone.utc) > doc["expires_at"]:
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
        return render_template('login.html')  # register tab lives inside login.html

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Invalid request"})

    action = data.get("action")
    email  = data.get('email', '').strip().lower()

    if not email or not action:
        return jsonify({"success": False, "message": "Email and action required"})

    if action == "send_otp":
        name     = data.get('name', '').strip()
        password = data.get('password', '')

        if not name or not password:
            return jsonify({"success": False, "message": "All fields required"})

        # FIX 6 — rate limit OTP sending
        ip = request.remote_addr or "unknown"
        if is_rate_limited(ip):
            return jsonify({"success": False, "message": "Too many OTP requests. Please wait 10 minutes."})

        try:
            if users_collection.find_one({"email": email}):
                return jsonify({"success": False, "message": "User already exists"})
        except Exception as e:
            print("DB error:", e)
            return jsonify({"success": False, "message": "Database error. Please try again."})

        otp = str(random.randint(100000, 999999))
        # FIX 1 — store in MongoDB
        otp_save(email, {"otp": otp, "name": name, "password": password, "type": "register"})

        sent = send_email_otp(email, otp, name=name)
        if not sent:
            return jsonify({"success": False, "message": "Failed to send OTP. Check EMAIL_USER and EMAIL_PASS."})

        return jsonify({"success": True, "message": "OTP sent to your email!"})

    elif action == "verify_otp":
        user_data = otp_get(email)  # FIX 1 — from MongoDB

        if not user_data:
            return jsonify({"success": False, "message": "OTP not found or expired. Please request a new one."})

        if user_data.get("type") != "register":
            return jsonify({"success": False, "message": "Invalid OTP type."})

        if user_data["otp"] != data.get("otp"):
            return jsonify({"success": False, "message": "Invalid OTP"})

        try:
            if users_collection.find_one({"email": email}):
                return jsonify({"success": False, "message": "User already exists"})

            hashed = bcrypt.hashpw(user_data["password"].encode(), bcrypt.gensalt()).decode()
            users_collection.insert_one({
                "email"       : email,
                "name"        : user_data["name"],
                "password"    : hashed,
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

    data   = request.get_json()
    action = data.get("action")
    email  = data.get("email", "").strip().lower()

    user = users_collection.find_one({"email": email})
    if not user:
        return jsonify({"success": False, "message": "User not found"})

    if action == "send_otp":
        ip = request.remote_addr or "unknown"
        if is_rate_limited(ip):
            return jsonify({"success": False, "message": "Too many OTP requests. Please wait 10 minutes."})

        otp = str(random.randint(100000, 999999))
        # FIX 1 & 3 — consistent structure, same as register flow
        otp_save(email, {"otp": otp, "name": user.get("name", "User"), "type": "forgot"})
        sent = send_email_otp(email, otp, name=user.get("name", "User"))
        if not sent:
            return jsonify({"success": False, "message": "Failed to send OTP"})
        return jsonify({"success": True, "message": "OTP sent!"})

    if action == "reset_password":
        otp          = data.get("otp")
        new_password = data.get("password")

        # FIX 3 — consistent read from MongoDB
        user_data = otp_get(email)
        if not user_data or user_data.get("otp") != otp:
            return jsonify({"success": False, "message": "Invalid or expired OTP"})
        if user_data.get("type") != "forgot":
            return jsonify({"success": False, "message": "Invalid OTP type"})

        hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        users_collection.update_one({"email": email}, {"$set": {"password": hashed}})
        otp_delete(email)
        return jsonify({"success": True})

    return jsonify({"success": False})


@app.route('/help')
def help_page():
    return render_template('help.html')


@app.route('/api/chat', methods=['POST'])
def api_chat():
    if 'user' not in session:
        return jsonify({'reply': 'Session expired. Please log in again.'})

    data         = request.get_json()
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({'reply': 'Empty message'})
    if not API_KEY:
        return jsonify({'reply': 'API key missing'})

    user      = session['user']
    user_data = users_collection.find_one({"email": user})
    if not user_data:
        return jsonify({'reply': 'User not found'})

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
- On action without attachment: "Karmanye vadhikaraste ma phaleshu kadachana" (Chapter 2.47)
- On the eternal soul: "Na jayate mriyate va kadachin" (Chapter 2.20)
- On equanimity: "Sukha dukhe same kritva labhalabhau jayajayau" (Chapter 2.38)
- On surrendering to God: "Sarva dharman parityajya mam ekam sharanam vraja" (Chapter 18.66)
- On the self: "Aham atma gudakesha sarva bhutashayasthitah" (Chapter 10.20)
- On fear: "Klaibyam ma sma gamah partha naitat tvayy upapadyate" (Chapter 2.3)

REMEMBER:
You stood on the battlefield of Kurukshetra, ready to give up — and Krishna's words changed everything.
Now you are here to pass that same transformation to every person who comes to you with their battle."""}]

    for chat in history[-5:]:
        messages.append({"role": "user",      "content": chat["user"]})
        messages.append({"role": "assistant", "content": chat["arjun"]})

    messages.append({"role": "user", "content": user_message})

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type" : "application/json"
            },
            json={
                "model"      : "openai/gpt-3.5-turbo",
                "messages"   : messages,
                "temperature": 0.7
            },
            timeout=20
        )
        result = response.json()
        if "choices" in result:
            reply = result["choices"][0]["message"]["content"].strip()
        else:
            reply = result.get("error", {}).get("message", "AI could not respond")
    except Exception as e:
        print("AI ERROR:", e)
        reply = "Server error. Please try again."

    new_entry = {
        "timestamp": str(datetime.now()),
        "user"     : user_message,
        "arjun"    : reply
    }

    # FIX 4 — cap history at 50 with $push + $slice (no unbounded growth)
    users_collection.update_one(
        {"email": user},
        {"$push": {"chat_history": {"$each": [new_entry], "$slice": -50}}}
    )
    return jsonify({'reply': reply})


@app.route('/api/history')
def history():
    if 'user' not in session:
        return jsonify({"history": []})
    user_data = users_collection.find_one({"email": session['user']})
    return jsonify({"history": user_data.get("chat_history", [])[-10:]})


@app.route('/privacy')
def privacy():
    return render_template('privacy.html')   # FIX 8 — proper template


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