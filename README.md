# 🧠 Arjun AI — GitaPath

A modern AI-powered chatbot inspired by the wisdom of the Bhagavad Gita.
Arjun acts as a calm, thoughtful guide — offering practical advice with emotional intelligence.

---

## 🚀 Live Demo

👉 https://arjun-ai.onrender.com

---

## ✨ Features

* 🧠 AI Chat (OpenRouter API)
* 💬 Emotion-aware responses
* 📜 Gita-inspired wisdom (contextual)
* 🔐 User Authentication (Login / Register)
* 🔁 Password Reset with OTP (Email)
* 🧾 Chat History (MongoDB)
* 🌐 Fully deployed on Render

---

## 🏗️ Tech Stack

* **Backend:** Flask (Python)
* **Database:** MongoDB Atlas
* **AI API:** OpenRouter
* **Frontend:** HTML, CSS, JavaScript
* **Authentication:** Session-based + bcrypt

---

## 📂 Project Structure

```
├── app.py
├── requirements.txt
├── templates/
│   ├── login.html
│   ├── register.html
│   ├── chat.html
│   ├── forgot.html
│   └── help.html
├── static/ (optional)
└── README.md
```

---

## ⚙️ Environment Variables

Create these in Render or `.env`:

```
OPENROUTER_API_KEY=your_api_key
MONGO_URI=your_mongodb_uri
EMAIL_USER=your_email@gmail.com
EMAIL_PASS=your_app_password
```

---

## 🛠️ Installation (Local Setup)

```bash
git clone https://github.com/OSubhajit/Arjun-ai.git
cd Arjun-ai

python -m venv venv
venv\Scripts\activate   # Windows

pip install -r requirements.txt
```

---

## ▶️ Run the App

```bash
python app.py
```

Then open:

```
http://127.0.0.1:5000
```

---

## 🌍 Deployment (Render)

1. Push code to GitHub
2. Go to https://render.com
3. Create **Web Service**
4. Connect repo
5. Set:

   * Build Command: `pip install -r requirements.txt`
   * Start Command: `python app.py`
6. Add Environment Variables
7. Deploy 🚀

---

## 🧠 AI Behavior

Arjun:

* Talks like a human friend
* Understands emotions
* Gives practical advice first
* Uses Gita wisdom only when needed

---

## 🔐 Security Notes

* Passwords are hashed using bcrypt
* Sensitive keys stored in environment variables
* MongoDB secured via IP access control

---

## 📌 Future Improvements

* 📊 Admin dashboard
* 📱 Mobile app (React Native)
* 🎙️ Voice assistant integration
* 🧠 Better long-term memory
* 📈 Analytics & user insights

---

## 👤 Author

**Subhajit Sarkar**
📧 [subhajitsarkar0708@gmail.com](mailto:subhajitsarkar0708@gmail.com)

---

## ⭐ Support

If you like this project, give it a ⭐ on GitHub!
