<div align="center">

<img src="https://img.shields.io/badge/GitaPath-Arjun%20AI-orange?style=for-the-badge&logo=hinduism" alt="GitaPath"/>

# 🏹 GitaPath — Arjun AI

### *Speak with Arjun. Find wisdom for your battle.*

An AI-powered spiritual guide built on the Bhagavad Gita — embodying Arjun, the legendary warrior of Kurukshetra, powered by OpenRouter LLMs and deployed on Render.

<br/>

[![Live Demo](https://img.shields.io/badge/🚀%20Live%20Demo-arjun--ai.onrender.com-brightgreen?style=for-the-badge)](https://arjun-ai.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.1.0-black?style=flat-square&logo=flask)](https://flask.palletsprojects.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-green?style=flat-square&logo=mongodb)](https://mongodb.com)
[![Render](https://img.shields.io/badge/Deployed-Render-purple?style=flat-square&logo=render)](https://render.com)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

<br/>

> *"कर्मण्येवाधिकारस्ते मा फलेषु कदाचन"*
> "You have the right to act, but never to the fruits of action." — Gita 2.47

</div>

---

## 📖 What is GitaPath?

**GitaPath** is a full-stack AI web application where users can have a personal conversation with **Arjun** — the legendary warrior from the Mahabharata and the disciple of Lord Krishna. Arjun speaks using the timeless wisdom of all **18 chapters of the Bhagavad Gita**, applying it to real modern-day problems like stress, heartbreak, purpose, fear, and anger.

This is not just another chatbot. Arjun has a personality, a history, and a soul. He stood on the battlefield of Kurukshetra ready to give up — and was transformed by Krishna's words. He now passes that same transformation to every user who comes with their battle.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🏹 **Arjun AI Chat** | Conversational AI that stays fully in character as Arjun — never breaks role |
| 📜 **Bhagavad Gita Wisdom** | Quotes relevant Sanskrit shlokas with meaning in natural conversation |
| 🔐 **Secure Auth System** | Register, Login, Logout with bcrypt-hashed passwords and session management |
| 📧 **OTP Email Verification** | Email-based OTP for registration and password reset via Google Apps Script |
| 🗂 **Conversation History** | All chats saved to MongoDB, grouped by date, viewable in sidebar |
| 👤 **User Profile Page** | Shows total messages, sessions, and full conversation history |
| 🔊 **Voice Input & Output** | Speak your question (Web Speech API) and hear Arjun's response |
| 📱 **Mobile Responsive** | Fully responsive layout with collapsible sidebar for mobile |
| 🌐 **Production Deployed** | Live on Render with Gunicorn, connected to MongoDB Atlas |
| 🛡️ **Security Hardened** | Rate limiting, XSS protection, constant-time OTP comparison, no plaintext passwords |

---

## 🎯 Live Demo

👉 **[https://arjun-ai.onrender.com](https://arjun-ai.onrender.com)**

> ⚠️ Hosted on Render free tier — may take **30–60 seconds** to wake up on first visit.

**Try asking Arjun:**
- *"I feel like giving up on everything"*
- *"What does the Gita say about fear?"*
- *"I am heartbroken and lost"*
- *"Explain karma to me in simple words"*

---

## 🏗️ Tech Stack

```
┌─────────────────────────────────────────────────────────┐
│                        Frontend                         │
│         HTML5 · CSS3 · Vanilla JS · Web Speech API      │
├─────────────────────────────────────────────────────────┤
│                        Backend                          │
│              Flask 3.1 · Python 3.10+ · Gunicorn        │
├─────────────────────────────────────────────────────────┤
│                       Database                          │
│           MongoDB Atlas (pymongo) · TTL Indexes         │
├─────────────────────────────────────────────────────────┤
│                      AI / Email                         │
│       OpenRouter API · Google Apps Script (Gmail)       │
├─────────────────────────────────────────────────────────┤
│                      Deployment                         │
│                   Render (free tier)                    │
└─────────────────────────────────────────────────────────┘
```

---

## 📂 Project Structure

```
Arjun-ai/
│
├── app.py                  # Main Flask application — all routes, auth, AI logic
├── requirements.txt        # Python dependencies
├── Procfile                # Gunicorn start command for Render
├── .gitignore              # Excludes .env, __pycache__, venv
│
├── templates/
│   ├── login.html          # Login + Register (tabbed, single page)
│   ├── chat.html           # Main chat UI with sidebar and voice
│   ├── forgot.html         # Forgot password + OTP reset
│   ├── profile.html        # User profile + conversation history
│   ├── help.html           # Help / FAQ page
│   ├── privacy.html        # Privacy policy
│   └── email.html          # OTP email template
│
└── static/
    └── style.css           # All styles — dark theme, animations, responsive
```

---

## ⚙️ Environment Variables

Create a `.env` file in the root directory (never commit this to GitHub):

```env
# ── Required ──────────────────────────────────────────
MONGO_URI=mongodb+srv://<user>:<pass>@cluster.mongodb.net/OSubhajit
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxx
SECRET_KEY=your_random_64_char_hex_string
GMAIL_SCRIPT_URL=https://script.google.com/macros/s/XXXX/exec

# ── Optional (with defaults) ───────────────────────────
AI_MODEL=openai/gpt-3.5-turbo        # or meta-llama/llama-3.3-70b-instruct:free
```

> **Generate a secure SECRET_KEY:**
> ```bash
> python -c "import secrets; print(secrets.token_hex(32))"
> ```

### On Render — add the same keys under **Environment → Add Environment Variable**

| Key | Notes |
|-----|-------|
| `MONGO_URI` | MongoDB Atlas connection string |
| `OPENROUTER_API_KEY` | Get from [openrouter.ai/keys](https://openrouter.ai/keys) |
| `SECRET_KEY` | Generate with command above — **required** in production |
| `GMAIL_SCRIPT_URL` | Your deployed Google Apps Script webhook URL |
| `AI_MODEL` | Optional — defaults to `openai/gpt-3.5-turbo` |

---

## 🛠️ Local Setup

### 1. Clone the repository
```bash
git clone https://github.com/OSubhajit/Arjun-ai.git
cd Arjun-ai
```

### 2. Create and activate a virtual environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Create your `.env` file
```bash
cp .env.example .env   # if example exists, or create manually
# Fill in MONGO_URI, OPENROUTER_API_KEY, SECRET_KEY, GMAIL_SCRIPT_URL
```

### 5. Run the app
```bash
python app.py
```

Open your browser at:
```
http://127.0.0.1:5000
```

---

## 🌍 Deployment on Render

1. Push your code to GitHub
2. Go to [render.com](https://render.com) → **New → Web Service**
3. Connect your GitHub repo `OSubhajit/Arjun-ai`
4. Configure:

   | Setting | Value |
   |---------|-------|
   | **Environment** | Python |
   | **Build Command** | `pip install -r requirements.txt` |
   | **Start Command** | `gunicorn app:app` |
   | **Instance Type** | Free |

5. Add all **Environment Variables** (see table above)
6. Click **Deploy** 🚀

> Render auto-deploys every time you push to `main`.

---

## 🔐 Security Architecture

| Layer | Implementation |
|-------|---------------|
| **Passwords** | bcrypt hashed with salt — never stored as plaintext |
| **OTP Storage** | Hashed before saving to MongoDB; TTL index auto-expires in 10 min |
| **OTP Generation** | `secrets.randbelow()` — cryptographically secure random |
| **OTP Comparison** | `hmac.compare_digest()` — constant-time, prevents timing attacks |
| **Rate Limiting** | MongoDB-backed — works across all Gunicorn workers (not in-memory) |
| **Session Security** | `SESSION_COOKIE_HTTPONLY=True`, `SAMESITE=Lax`, `SECURE=True` on HTTPS |
| **XSS Prevention** | All user/AI text escaped via `escapeHtml()` before DOM insertion |
| **Secret Key** | App refuses to start in production if `SECRET_KEY` env var is missing |
| **Email Enumeration** | Forgot password always returns same response — doesn't reveal registered emails |
| **Message Limits** | API chat endpoint rejects messages over 2000 characters |

---

## 🧠 How the AI Works

Arjun is powered by an **OpenRouter LLM** with a deep system prompt that defines his complete character, knowledge base, and communication style.

```
User message
     │
     ▼
Flask /api/chat endpoint
     │
     ├── Auth check (session)
     ├── Message length limit (2000 chars)
     ├── Load last 5 chat turns from MongoDB (projection)
     │
     ▼
OpenRouter API (GPT-3.5-turbo / Llama 3.3 70B)
  System prompt: Arjun's full character + Gita knowledge
  Last 5 turns: conversation context
  User message: current question
     │
     ▼
Reply saved to MongoDB (capped at 50 entries with $slice)
     │
     ▼
JSON response → rendered in chat UI
     │
     └── Devanagari runs wrapped in shloka box
     └── Web Speech API reads the reply aloud (if voice enabled)
```

---

## 📸 Screenshots

| Chat Interface | Profile Page |
|---|---|
| ![chat](https://arjun-ai.onrender.com) | ![profile](https://arjun-ai.onrender.com/profile) |

> *(Visit the live demo to see the full UI)*

---

## 🔮 Roadmap

- [ ] 📊 Admin dashboard with user analytics
- [ ] 🧠 Longer memory using vector search (MongoDB Atlas Vector)
- [ ] 📖 Full Bhagavad Gita shloka database (all 700 verses)
- [ ] 🌐 Hindi / Bengali language support
- [ ] 📱 React Native mobile app
- [ ] 🎙️ Full voice conversation mode (STT + TTS)
- [ ] 🔔 Daily wisdom notification system

---

## 📦 Dependencies

```txt
Flask==3.1.0
pymongo==4.16.0
requests==2.32.3
python-dotenv==1.1.0
bcrypt==4.0.1
dnspython
gunicorn
```

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "Add: your feature"`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 👤 Author

<div align="center">

**Subhajit Sarkar**

*CSE Student · Aspiring Penetration Tester · Builder*

[![GitHub](https://img.shields.io/badge/GitHub-OSubhajit-black?style=flat-square&logo=github)](https://github.com/OSubhajit)

</div>

---

<div align="center">

If this project helped you or inspired you, please consider giving it a ⭐ on GitHub!

*"The soul is never born nor dies at any time. It has not come into being, does not come into being, and will not come into being. It is unborn, eternal, ever-existing, and primeval."*
*— Bhagavad Gita 2.20*

</div>
