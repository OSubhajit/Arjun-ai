# Arjun AI 🏹

> *"I am here to pass that same transformation to every person who comes to me with their battle."*

Arjun AI is a full-stack web application that lets you have a deeply personal conversation with **Arjun** — the legendary warrior of Kurukshetra — who answers your questions through the lens of the **Bhagavad Gita**. Powered by a large language model via OpenRouter, Arjun responds with empathy, relevant Sanskrit shlokas, and practical wisdom drawn from all 18 chapters of the Gita.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [Local Development](#local-development)
- [Docker](#docker)
- [Deploying to Render](#deploying-to-render)
- [Email OTP Setup (Google Apps Script)](#email-otp-setup-google-apps-script)
- [Running Tests](#running-tests)
- [API Reference](#api-reference)
- [Security Overview](#security-overview)
- [Rate Limits](#rate-limits)
- [Multi-language Support](#multi-language-support)
- [License](#license)

---

## Features

- 🧘 **AI persona chat** — Converse with Arjun who responds with Bhagavad Gita wisdom, Sanskrit shlokas, and modern-life guidance
- 🔐 **Secure authentication** — Email + password registration with bcrypt hashing, OTP email verification, and "forgot password" flow
- 🌐 **Multi-language responses** — Supports 50+ languages; Arjun replies in your chosen language while keeping Sanskrit shlokas in their original script
- 📜 **Persistent conversation history** — Sessions are stored per user in MongoDB, grouped by session ID, and viewable in a profile dashboard
- 🛡️ **Production-ready security** — CSRF protection, secure session cookies, HTTP security headers, and per-IP rate limiting on all sensitive endpoints
- 🐳 **Docker support** — Ships with a `Dockerfile` and `docker-compose.yml` for one-command local dev with MongoDB included
- 🚀 **Render-ready deployment** — Ships with a `Procfile` for Gunicorn; zero extra configuration needed

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | Flask 3.1 (Blueprint architecture) |
| Database | MongoDB (via PyMongo 4.16) |
| AI backend | OpenRouter API (model-agnostic) |
| Password hashing | bcrypt 4.0 |
| Email OTP delivery | Google Apps Script webhook |
| Production server | Gunicorn 23.0 |
| Environment config | python-dotenv |
| Testing | pytest + mongomock |

---

## Project Structure

```
Arjun-ai/
│
├── app.py                          # Flask factory — wires blueprints together (60 lines)
├── config.py                       # All environment variables and language registry
├── extensions.py                   # MongoDB connection + structured logging setup
│
├── blueprints/                     # Route logic split by feature
│   ├── auth/routes.py              # Login, register, forgot password, logout
│   ├── chat/routes.py              # Chat page, /api/chat, /api/history
│   ├── profile/routes.py           # Profile page, /api/profile, /api/conversations
│   └── main/routes.py              # Index, help, privacy, CSRF token endpoint
│
├── utils/
│   ├── security.py                 # CSRF, rate limiting, OTP helpers
│   ├── email.py                    # OTP email dispatch via Google Apps Script
│   └── history.py                  # Conversation grouping helpers
│
├── static/
│   ├── style.css                   # Global stylesheet (CSS variables throughout)
│   └── js/
│       ├── csrf.js                 # Fetch monkey-patch — auto-injects CSRF token
│       ├── chat.js                 # Chat UI, Three.js background, voice, language picker
│       ├── register.js             # Two-step OTP registration flow
│       ├── forgot.js               # Password reset flow
│       └── profile.js              # Profile dashboard and conversation history
│
├── templates/
│   ├── base.html                   # Single base template — fonts, CSRF, AdSense, headers
│   ├── chat.html                   # Main chat interface
│   ├── login.html                  # Login page
│   ├── register.html               # Registration + OTP verification
│   ├── forgot.html                 # Password reset
│   ├── profile.html                # User dashboard & conversation history
│   ├── help.html                   # Help / FAQ page
│   ├── privacy.html                # Privacy policy
│   └── email.html                  # OTP email template (standalone, not extended)
│
├── tests/
│   ├── conftest.py                 # Fixtures: app, client, registered user, mongomock
│   ├── test_auth.py                # Login, register, forgot password, logout tests
│   ├── test_chat.py                # Chat API and rate limiting tests
│   ├── test_profile.py             # Profile and conversations API tests
│   └── test_security.py            # CSRF, security headers, input sanitisation tests
│
├── Dockerfile                      # Two-stage production image (non-root user)
├── docker-compose.yml              # Local dev stack: app + MongoDB
├── Procfile                        # Gunicorn startup for Render
├── requirements.txt                # Production dependencies
├── requirements-dev.txt            # Dev dependencies: pytest, black, ruff, mypy
├── .env.example                    # Template for all environment variables
└── .gitignore
```

---

## Prerequisites

- Python 3.10 or higher
- A running MongoDB instance (local or [MongoDB Atlas](https://www.mongodb.com/atlas))
- An [OpenRouter](https://openrouter.ai/) account and API key
- A Google account for the OTP email webhook (see [Email OTP Setup](#email-otp-setup-google-apps-script))

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values. **Never commit `.env`** — it is already in `.gitignore`.

```env
# ── Required ──────────────────────────────────────────────────────────────────
MONGO_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/<dbname>?retryWrites=true&w=majority
OPENROUTER_API_KEY=sk-or-...
SECRET_KEY=a_long_random_secret_string

# ── Optional — defaults shown ─────────────────────────────────────────────────
AI_MODEL=openai/gpt-3.5-turbo
GMAIL_SCRIPT_URL=
ADSENSE_PUB_ID=
PORT=5000
```

### Variable reference

| Variable | Required | Description |
|---|---|---|
| `MONGO_URI` | ✅ | MongoDB connection string. App exits on startup if missing. |
| `OPENROUTER_API_KEY` | ✅ | API key for OpenRouter. Chat endpoint returns 500 if missing. |
| `SECRET_KEY` | ✅ in prod | Flask session signing key. App exits in production if missing; uses a dev default locally. |
| `AI_MODEL` | ❌ | LLM model slug passed to OpenRouter. Defaults to `openai/gpt-3.5-turbo`. |
| `GMAIL_SCRIPT_URL` | ❌ | Google Apps Script webhook URL for OTP emails. OTP flows fail silently if not set. |
| `ADSENSE_PUB_ID` | ❌ | Google AdSense publisher ID (e.g. `ca-pub-XXXXXXXXXXXXXXXX`). Leave blank to disable all ad tags. |
| `RENDER` | ❌ | Set to `"true"` automatically by Render. Enables secure cookies and disables debug mode. |
| `PORT` | ❌ | Local development port. Defaults to `5000`. |

---

## Local Development

**1. Clone the repository**

```bash
git clone https://github.com/OSubhajit/Arjun-ai.git
cd Arjun-ai
```

**2. Create and activate a virtual environment**

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Configure environment variables**

```bash
cp .env.example .env
# Fill in MONGO_URI, OPENROUTER_API_KEY, and SECRET_KEY
```

**5. Run the development server**

```bash
python app.py
```

The app will be available at `http://localhost:5000`. On startup you will see structured logs confirming all services are connected:

```
2026-05-06 08:00:00 [INFO] config: === STARTUP ===
2026-05-06 08:00:00 [INFO] config: MONGO_URI        : set
2026-05-06 08:00:00 [INFO] config: API_KEY          : set
2026-05-06 08:00:00 [INFO] config: AI_MODEL         : openai/gpt-3.5-turbo
2026-05-06 08:00:00 [INFO] config: ADSENSE_PUB_ID   : (not set — ads disabled)
2026-05-06 08:00:00 [INFO] config: IS_PROD          : False
2026-05-06 08:00:00 [INFO] extensions: MongoDB connected
2026-05-06 08:00:00 [INFO] extensions: unique email index ready
2026-05-06 08:00:00 [INFO] extensions: OTP TTL index ready
2026-05-06 08:00:00 [INFO] extensions: rate-limit TTL index ready
```

---

## Docker

Run the full stack (app + MongoDB) with a single command — no local MongoDB installation needed.

```bash
# Copy and fill in your env vars
cp .env.example .env

# Start everything
docker compose up --build
```

The app will be available at `http://localhost:5000`. MongoDB data is persisted in a Docker volume (`mongo_data`) so it survives container restarts.

To stop:

```bash
docker compose down
```

---

## Deploying to Render

The repository ships with a `Procfile` that tells Render how to start the app:

```
web: gunicorn app:app --workers 2 --timeout 60
```

**Step-by-step**

1. Push your code to GitHub.
2. Go to [Render](https://render.com/) → **New Web Service** → connect your repo.
3. Set **Build Command** to `pip install -r requirements.txt`.
4. Set **Start Command** to `gunicorn app:app --workers 2 --timeout 60` (Render also reads the `Procfile` automatically).
5. Add all required **Environment Variables** in the Render dashboard.
6. Deploy. Render will connect to MongoDB, verify the API key, and bring the app online.

> **Tip:** Use [MongoDB Atlas](https://www.mongodb.com/atlas) for a free cloud-hosted database that works seamlessly with Render.

---

## Email OTP Setup (Google Apps Script)

Arjun AI sends OTP emails through a **Google Apps Script webhook** — no paid SMTP service required.

**1. Open Google Apps Script**

Go to [script.google.com](https://script.google.com) and create a new project.

**2. Paste the following script**

```javascript
function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    const { to, name, otp } = data;

    GmailApp.sendEmail(to, "Your Arjun AI OTP Code", "", {
      htmlBody: `<p>Hello ${name},</p>
                 <p>Your OTP is: <strong>${otp}</strong></p>
                 <p>It expires in 10 minutes.</p>`
    });

    return ContentService
      .createTextOutput(JSON.stringify({ success: true }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ success: false, error: err.message }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
```

**3. Deploy as a Web App**

- Click **Deploy → New Deployment**.
- Set **Execute as**: *Me* and **Who has access**: *Anyone*.
- Click **Deploy** and copy the web app URL.

**4. Add the URL to your `.env`**

```env
GMAIL_SCRIPT_URL=https://script.google.com/macros/s/.../exec
```

> Emails will be sent from the Google account that owns the Apps Script project.

---

## Running Tests

The test suite uses `pytest` and `mongomock` — no live database or API key required.

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage report
pytest --cov=. --cov-report=term-missing

# Run a specific test file
pytest tests/test_auth.py -v
```

The suite covers 30 test cases across four files:

| File | What it tests |
|---|---|
| `tests/test_auth.py` | Login, register OTP flow, forgot password, logout |
| `tests/test_chat.py` | Chat API, history, AI timeout handling |
| `tests/test_profile.py` | Profile page, conversations API, delete |
| `tests/test_security.py` | CSRF protection, security headers, XSS sanitisation |

---

## API Reference

All endpoints that mutate state require a valid **CSRF token** in the `X-CSRF-Token` request header. Fetch it first from `GET /api/csrf-token`.

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/login` | Render login page |
| `POST` | `/login` | Authenticate user. Body: `{ email, password, rememberMe }` |
| `GET` | `/register` | Render registration page |
| `POST` | `/register` | Two-step flow. Body: `{ action: "send_otp", email, name, password }` then `{ action: "verify_otp", email, otp }` |
| `GET` | `/forgot` | Render password reset page |
| `POST` | `/forgot` | Two-step flow. Body: `{ action: "send_otp", email }` then `{ action: "reset_password", email, otp, password }` |
| `POST` | `/logout` | Clear session. Requires CSRF token. |

### Chat

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/chat` | Render the chat interface (authenticated) |
| `POST` | `/api/chat` | Send a message to Arjun. Body: `{ message, language, session_id }`. Returns `{ reply }`. |
| `GET` | `/api/history` | Fetch the last 10 chat entries for the current session. |

### Profile & Conversations

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/profile` | Render the profile/dashboard page (authenticated) |
| `GET` | `/api/profile` | Returns `{ name, email, total_messages, total_sessions, conversations }` |
| `GET` | `/api/conversations` | Returns all conversations grouped by session |
| `DELETE` | `/api/conversations/<id>` | Delete a conversation by session ID or date string |

### Utility

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/csrf-token` | Returns `{ csrf_token }` for use in subsequent mutating requests |
| `GET` | `/help` | Render the help page |
| `GET` | `/privacy` | Render the privacy policy page |

---

## Security Overview

**CSRF protection** — Every state-changing endpoint validates a `X-CSRF-Token` header against the server-side session token using `hmac.compare_digest`, preventing timing-based attacks.

**Secure session cookies** — In production (`RENDER=true`), cookies are flagged `Secure`, `HttpOnly`, and `SameSite=Lax`. Sessions last 7 days when "Remember me" is checked.

**Password hashing** — All passwords are stored as bcrypt hashes. Plaintext passwords are never persisted anywhere.

**OTP security** — OTPs are 6-digit codes generated with `secrets.randbelow` (cryptographically secure). They expire after 10 minutes via a MongoDB TTL index. Five failed attempts invalidate the OTP immediately.

**Input sanitisation** — User-supplied names are HTML-escaped with `markupsafe.escape` and truncated to 100 characters. Emails are validated with a strict regex. Message length is capped at 2,000 characters.

**HTTP security headers** — Applied globally via an `after_request` hook:

| Header | Value |
|---|---|
| `X-Frame-Options` | `DENY` |
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Content-Security-Policy` | Restricts scripts, styles, fonts, images, and frames to known safe origins |

**Proxy-aware IP detection** — The `X-Forwarded-For` header is honoured so that rate limits apply to real client IPs, not the proxy IP.

---

## Rate Limits

| Action | Limit | Window |
|---|---|---|
| OTP send (register / forgot password) | 3 requests | per IP, per 10 minutes |
| Login attempts | 10 attempts | per IP, per 15 minutes |
| Chat messages | 20 messages | per user account, per 60 seconds |

Rate limit counters are stored in the `rate_limits` MongoDB collection with a TTL index for automatic expiry — no cron jobs needed.

---

## Multi-language Support

Pass an IETF language tag in the `language` field of the `/api/chat` request body. Arjun will respond entirely in the requested language, while keeping Sanskrit shlokas in their original script.

**Indian languages** — `hi` Hindi, `bn` Bengali, `ta` Tamil, `te` Telugu, `mr` Marathi, `gu` Gujarati, `kn` Kannada, `ml` Malayalam, `pa` Punjabi, `or` Odia, `as` Assamese, `ur` Urdu

**European languages** — `es` Spanish, `fr` French, `de` German, `it` Italian, `pt` Portuguese, `ru` Russian, `nl` Dutch, `pl` Polish, `sv` Swedish, `no` Norwegian, `da` Danish, `fi` Finnish, `el` Greek, `ro` Romanian, `cs` Czech, `hu` Hungarian, `uk` Ukrainian, `tr` Turkish

**Asian / Pacific languages** — `ja` Japanese, `ko` Korean, `zh` Chinese, `id` Indonesian, `ms` Malay, `th` Thai, `vi` Vietnamese, `ar` Arabic, `fa` Persian, `he` Hebrew, `ne` Nepali, `si` Sinhala

**African languages** — `sw` Swahili, `af` Afrikaans

Unknown or malformed language codes fall back silently to English (`en`).

---

## License

This project is licensed under the terms found in the [LICENSE](LICENSE) file.

---

*Built with devotion. Guided by the Gita.*
