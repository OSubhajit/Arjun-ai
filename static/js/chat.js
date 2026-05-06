/**
 * chat.js — Arjun chat interface: history, messaging, voice, language picker,
 *            Three.js background, sidebar, conversation management.
 *
 * Globals injected by chat.html template:
 *   window.CHAT_USER_NAME  — current user's display name
 *   window.CHAT_STORY      — Mahabharata sidebar blurb
 */

// ── Language config ──────────────────────────────────────────────────────────
const LANGUAGES = {
  en: { name:'English',         flag:'🇬🇧', srLang:'en-IN', ttsLang:'en-GB', voices:['Google UK English Male','Microsoft George','Daniel','Arthur','Microsoft David'] },
  hi: { name:'हिंदी',          flag:'🇮🇳', srLang:'hi-IN', ttsLang:'hi-IN', voices:['Google हिन्दी','Microsoft Hemant','Lekha','Ravi'] },
  bn: { name:'বাংলা',          flag:'🇮🇳', srLang:'bn-IN', ttsLang:'bn-IN', voices:['Google বাংলা','Bangla India'] },
  ta: { name:'தமிழ்',         flag:'🇮🇳', srLang:'ta-IN', ttsLang:'ta-IN', voices:['Google தமிழ்','Tamil India','Latha'] },
  te: { name:'తెలుగు',        flag:'🇮🇳', srLang:'te-IN', ttsLang:'te-IN', voices:['Google తెలుగు','Telugu India'] },
  mr: { name:'मराठी',          flag:'🇮🇳', srLang:'mr-IN', ttsLang:'mr-IN', voices:['Google मराठी','Marathi India'] },
  gu: { name:'ગુજરાતી',       flag:'🇮🇳', srLang:'gu-IN', ttsLang:'gu-IN', voices:['Google ગુજરાતી','Gujarati India'] },
  kn: { name:'ಕನ್ನಡ',        flag:'🇮🇳', srLang:'kn-IN', ttsLang:'kn-IN', voices:['Google ಕನ್ನಡ','Kannada India'] },
  ml: { name:'മലയാളം',       flag:'🇮🇳', srLang:'ml-IN', ttsLang:'ml-IN', voices:['Google മലയാളം','Malayalam India'] },
  pa: { name:'ਪੰਜਾਬੀ',       flag:'🇮🇳', srLang:'pa-IN', ttsLang:'pa-IN', voices:['Google ਪੰਜਾਬੀ','Punjabi India'] },
  or: { name:'ଓଡ଼ିଆ',        flag:'🇮🇳', srLang:'or-IN', ttsLang:'or-IN', voices:[] },
  as: { name:'অসমীয়া',      flag:'🇮🇳', srLang:'as-IN', ttsLang:'as-IN', voices:[] },
  ur: { name:'اردو',           flag:'🇵🇰', srLang:'ur-PK', ttsLang:'ur-PK', voices:['Microsoft Rizwan','Urdu Pakistan'] },
  ne: { name:'नेपाली',         flag:'🇳🇵', srLang:'ne-NP', ttsLang:'ne-NP', voices:[] },
  si: { name:'සිංහල',         flag:'🇱🇰', srLang:'si-LK', ttsLang:'si-LK', voices:[] },
  zh: { name:'中文',            flag:'🇨🇳', srLang:'zh-CN', ttsLang:'zh-CN', voices:['Google 普通话（中国大陆）','Microsoft Huihui','Ting-Ting'] },
  ja: { name:'日本語',          flag:'🇯🇵', srLang:'ja-JP', ttsLang:'ja-JP', voices:['Google 日本語','Kyoko','Otoya','Microsoft Ichiro'] },
  ko: { name:'한국어',          flag:'🇰🇷', srLang:'ko-KR', ttsLang:'ko-KR', voices:['Google 한국의','Microsoft Heami','Yuna'] },
  th: { name:'ไทย',            flag:'🇹🇭', srLang:'th-TH', ttsLang:'th-TH', voices:['Google ภาษาไทย','Kanya'] },
  vi: { name:'Tiếng Việt',     flag:'🇻🇳', srLang:'vi-VN', ttsLang:'vi-VN', voices:['Google tiếng Việt','An'] },
  id: { name:'Bahasa Indonesia',flag:'🇮🇩', srLang:'id-ID', ttsLang:'id-ID', voices:['Google Bahasa Indonesia','Damayanti'] },
  ms: { name:'Bahasa Melayu',  flag:'🇲🇾', srLang:'ms-MY', ttsLang:'ms-MY', voices:['Google Bahasa Melayu'] },
  ar: { name:'العربية',        flag:'🇸🇦', srLang:'ar-SA', ttsLang:'ar-SA', voices:['Google عربي','Microsoft Naayf'] },
  fa: { name:'فارسی',          flag:'🇮🇷', srLang:'fa-IR', ttsLang:'fa-IR', voices:['Google فارسی','Microsoft Ava'] },
  he: { name:'עברית',          flag:'🇮🇱', srLang:'he-IL', ttsLang:'he-IL', voices:['Google עברית','Carmit'] },
  tr: { name:'Türkçe',         flag:'🇹🇷', srLang:'tr-TR', ttsLang:'tr-TR', voices:['Google Türkçe','Yelda','Microsoft Tolga'] },
  es: { name:'Español',        flag:'🇪🇸', srLang:'es-ES', ttsLang:'es-ES', voices:['Google español de Estados Unidos','Mónica','Jorge','Microsoft Pablo'] },
  fr: { name:'Français',       flag:'🇫🇷', srLang:'fr-FR', ttsLang:'fr-FR', voices:['Google français','Thomas','Amelie','Microsoft Paul'] },
  de: { name:'Deutsch',        flag:'🇩🇪', srLang:'de-DE', ttsLang:'de-DE', voices:['Google Deutsch','Anna','Markus','Microsoft Stefan'] },
  it: { name:'Italiano',       flag:'🇮🇹', srLang:'it-IT', ttsLang:'it-IT', voices:['Google italiano','Alice','Luca','Microsoft Cosimo'] },
  pt: { name:'Português',      flag:'🇵🇹', srLang:'pt-PT', ttsLang:'pt-PT', voices:['Google português do Brasil','Joana','Microsoft Helia'] },
  ru: { name:'Русский',        flag:'🇷🇺', srLang:'ru-RU', ttsLang:'ru-RU', voices:['Google русский','Milena','Yuri','Microsoft Irina'] },
  nl: { name:'Nederlands',     flag:'🇳🇱', srLang:'nl-NL', ttsLang:'nl-NL', voices:['Google Nederlands','Ellen','Microsoft Frank'] },
  pl: { name:'Polski',         flag:'🇵🇱', srLang:'pl-PL', ttsLang:'pl-PL', voices:['Google polski','Zosia','Microsoft Paulina'] },
  sv: { name:'Svenska',        flag:'🇸🇪', srLang:'sv-SE', ttsLang:'sv-SE', voices:['Google svenska','Alva','Microsoft Bengt'] },
  no: { name:'Norsk',          flag:'🇳🇴', srLang:'nb-NO', ttsLang:'nb-NO', voices:['Google norsk Bokmål','Nora','Microsoft Jon'] },
  da: { name:'Dansk',          flag:'🇩🇰', srLang:'da-DK', ttsLang:'da-DK', voices:['Google dansk','Sara','Microsoft Helle'] },
  fi: { name:'Suomi',          flag:'🇫🇮', srLang:'fi-FI', ttsLang:'fi-FI', voices:['Google suomi','Satu','Microsoft Heidi'] },
  el: { name:'Ελληνικά',      flag:'🇬🇷', srLang:'el-GR', ttsLang:'el-GR', voices:['Google ελληνικά','Melina','Microsoft Stefanos'] },
  ro: { name:'Română',         flag:'🇷🇴', srLang:'ro-RO', ttsLang:'ro-RO', voices:['Google română','Ioana','Microsoft Andrei'] },
  cs: { name:'Čeština',        flag:'🇨🇿', srLang:'cs-CZ', ttsLang:'cs-CZ', voices:['Google čeština','Zuzana','Microsoft Jakub'] },
  hu: { name:'Magyar',         flag:'🇭🇺', srLang:'hu-HU', ttsLang:'hu-HU', voices:['Google magyar','Mariska','Microsoft Szabolcs'] },
  uk: { name:'Українська',    flag:'🇺🇦', srLang:'uk-UA', ttsLang:'uk-UA', voices:['Google українська','Lesya'] },
  sr: { name:'Српски',         flag:'🇷🇸', srLang:'sr-RS', ttsLang:'sr-RS', voices:[] },
  hr: { name:'Hrvatski',       flag:'🇭🇷', srLang:'hr-HR', ttsLang:'hr-HR', voices:[] },
  sk: { name:'Slovenčina',     flag:'🇸🇰', srLang:'sk-SK', ttsLang:'sk-SK', voices:['Laura'] },
  bg: { name:'Български',     flag:'🇧🇬', srLang:'bg-BG', ttsLang:'bg-BG', voices:[] },
  sw: { name:'Kiswahili',      flag:'🇰🇪', srLang:'sw-KE', ttsLang:'sw-KE', voices:[] },
  af: { name:'Afrikaans',      flag:'🇿🇦', srLang:'af-ZA', ttsLang:'af-ZA', voices:['Microsoft Kobus'] },
};

const TTS_RATE = {
  en:0.78, hi:0.82, mr:0.82, bn:0.85, ta:0.85, te:0.85, kn:0.85, ml:0.85,
  gu:0.83, pa:0.83, or:0.83, as:0.83, ur:0.82, ne:0.82, si:0.82,
  zh:0.80, ja:0.80, ko:0.82, th:0.85, vi:0.85, id:0.88, ms:0.88,
  ar:0.80, fa:0.80, he:0.82, tr:0.85,
  es:0.90, fr:0.88, de:0.85, it:0.88, pt:0.88, ru:0.82, nl:0.87,
  pl:0.85, sv:0.87, no:0.87, da:0.87, fi:0.85, el:0.85, ro:0.85,
  cs:0.85, hu:0.85, uk:0.82, sr:0.85, hr:0.85, sk:0.85, bg:0.85,
  sw:0.87, af:0.87,
};

// ── State ────────────────────────────────────────────────────────────────────
const userName         = window.CHAT_USER_NAME || 'Friend';
const mahabharataStory = window.CHAT_STORY     || '';

let isTyping         = false;
let voiceEnabled     = true;
let allHistory       = [];
let currentSessionId = String(Date.now());
let activeSessionEl  = null;
let currentLang      = localStorage.getItem('arjun_lang') || 'en';

// ── Utilities ─────────────────────────────────────────────────────────────────
function escapeHtml(text) {
  const d = document.createElement('div');
  d.textContent = text;
  return d.innerHTML;
}

function showToast(text, bg, color) {
  bg    = bg    || 'rgba(212,160,23,0.95)';
  color = color || '#1a0a00';
  let t = document.getElementById('app-toast');
  if (!t) {
    t = document.createElement('div');
    t.id = 'app-toast';
    Object.assign(t.style, {
      position:'fixed', bottom:'80px', left:'50%',
      transform:'translateX(-50%) translateY(20px)',
      padding:'8px 18px', borderRadius:'20px', fontSize:'13px', fontWeight:'600',
      fontFamily:'"DM Sans",sans-serif', zIndex:'9999',
      boxShadow:'0 4px 20px rgba(0,0,0,0.4)',
      transition:'all 0.3s cubic-bezier(0.34,1.56,0.64,1)',
      opacity:'0', whiteSpace:'nowrap',
    });
    document.body.appendChild(t);
  }
  t.textContent     = text;
  t.style.background = bg;
  t.style.color     = color;
  t.style.opacity   = '0';
  t.style.transform = 'translateX(-50%) translateY(20px)';
  t.offsetHeight;
  t.style.opacity   = '1';
  t.style.transform = 'translateX(-50%) translateY(0)';
  clearTimeout(t._timer);
  t._timer = setTimeout(() => {
    t.style.opacity   = '0';
    t.style.transform = 'translateX(-50%) translateY(20px)';
  }, 2500);
}

// ── Init ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('user-initial').textContent  = userName.charAt(0).toUpperCase();
  document.getElementById('sidebar-story').textContent = mahabharataStory.substring(0, 500) + '…';
  applyLanguage(currentLang, false);
  loadHistory();
  if (window.speechSynthesis) {
    window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
    window.speechSynthesis.getVoices();
  }
});

// ── Language picker ───────────────────────────────────────────────────────────
function toggleLangDropdown() {
  if (isTyping) { showToast('⏳ Wait for Arjun to finish responding', '#8866cc'); return; }
  const dropdown = document.getElementById('langDropdown');
  const btn      = document.querySelector('.lang-btn');
  if (dropdown.classList.contains('open')) { dropdown.classList.remove('open'); return; }
  const rect   = btn.getBoundingClientRect();
  const dropW  = 210;
  dropdown.style.top  = (rect.bottom + 6) + 'px';
  dropdown.style.left = Math.max(4, rect.right - dropW) + 'px';
  dropdown.classList.add('open');
  const active = dropdown.querySelector('.lang-option.active');
  if (active) setTimeout(() => active.scrollIntoView({ block: 'nearest' }), 50);
}

document.addEventListener('click', (e) => {
  const wrapper  = document.getElementById('langWrapper');
  const dropdown = document.getElementById('langDropdown');
  if (wrapper && dropdown && !wrapper.contains(e.target) && !dropdown.contains(e.target)) {
    dropdown.classList.remove('open');
  }
  const sidebar = document.getElementById('sidebar');
  const menuBtn = document.querySelector('.menu-btn');
  if (window.innerWidth <= 768 && sidebar && menuBtn &&
      !sidebar.contains(e.target) && !menuBtn.contains(e.target)) {
    sidebar.classList.remove('open');
  }
});

function setLanguage(lang) {
  const cfg = LANGUAGES[lang];
  if (!cfg) return;
  if (window.speechSynthesis) window.speechSynthesis.cancel();
  currentLang = lang;
  localStorage.setItem('arjun_lang', lang);
  applyLanguage(lang, true);
  document.getElementById('langDropdown').classList.remove('open');
  const btn = document.querySelector('.lang-btn');
  btn.classList.add('switching');
  setTimeout(() => btn.classList.remove('switching'), 400);
}

function applyLanguage(lang, showNotif) {
  const cfg = LANGUAGES[lang] || LANGUAGES['en'];
  document.getElementById('langLabel').textContent = cfg.flag + ' ' + cfg.name;
  document.querySelectorAll('.lang-option').forEach(el => {
    el.classList.toggle('active', el.dataset.lang === lang);
  });
  if (showNotif) showToast('Language: ' + cfg.flag + ' ' + cfg.name, 'rgba(212,160,23,0.95)', '#1a0a00');
}

// ── Sidebar + voice toggle ────────────────────────────────────────────────────
function toggleSidebar() { document.getElementById('sidebar').classList.toggle('open'); }

function toggleVoice() {
  voiceEnabled = !voiceEnabled;
  const btn = document.getElementById('voiceToggle');
  btn.textContent = voiceEnabled ? '🔊 Voice' : '🔇 Muted';
  btn.classList.toggle('muted', !voiceEnabled);
  if (!voiceEnabled && window.speechSynthesis) window.speechSynthesis.cancel();
}

// ── New chat ──────────────────────────────────────────────────────────────────
function newChat() {
  if (window.speechSynthesis) window.speechSynthesis.cancel();
  const wrap = document.getElementById('messages');
  wrap.innerHTML = '';
  const d = document.createElement('div');
  d.className = 'intro-msg'; d.id = 'intro-section';
  d.innerHTML = `<div class="intro-lotus">🏹</div>
    <h2>Namaste, ${escapeHtml(userName)}</h2>
    <p>I am here. Tell me what weighs on your heart today.</p>
    <div class="intro-sanskrit">सर्वधर्मान्परित्यज्य मामेकं शरणं व्रज</div>
    <div class="intro-translation">"Abandon all duties and surrender unto Me alone." — Gita 18.66</div>`;
  wrap.appendChild(d);
  currentSessionId = String(Date.now());
  activeSessionEl  = null;
  document.querySelectorAll('.conv-item').forEach(el => el.classList.remove('active'));
  if (window.innerWidth <= 768) document.getElementById('sidebar').classList.remove('open');
}

// ── History ───────────────────────────────────────────────────────────────────
async function loadHistory() {
  try {
    const res  = await fetch('/api/conversations');
    const data = await res.json();
    allHistory = data.conversations || [];
    renderConvList();
    if (allHistory.length > 0) {
      const last = allHistory[allHistory.length - 1];
      if (last.messages && last.messages.length > 0) {
        currentSessionId = last.session_id || String(Date.now());
        activeSessionEl  = last.session_id;
        const intro = document.getElementById('intro-section');
        if (intro) intro.style.display = 'none';
        last.messages.forEach(m => { addMessage('user', m.user, m.timestamp); addMessage('arjun', m.arjun, m.timestamp); });
      }
    }
  } catch (e) { console.error('loadHistory error:', e); }
}

function syncLocalHistory(userMsg, arjunReply) {
  const ts    = new Date().toISOString();
  const entry = { user: userMsg, arjun: arjunReply, timestamp: ts };
  const existing = allHistory.find(g => g.session_id === currentSessionId);
  if (existing) {
    existing.messages.push(entry);
  } else {
    const label = new Date().toLocaleString('en-IN', { month:'short', day:'numeric', year:'numeric', hour:'2-digit', minute:'2-digit' });
    allHistory.push({ session_id: currentSessionId, label, date: ts.slice(0,10), messages:[entry] });
  }
  renderConvList(currentSessionId);
}

function renderConvList(highlightSessionId) {
  const list = document.getElementById('conv-list');
  if (!allHistory || allHistory.length === 0) {
    list.innerHTML = '<div class="conv-empty">No conversations yet</div>'; return;
  }
  list.innerHTML = '';
  [...allHistory].reverse().forEach((conv, i) => {
    const item     = document.createElement('div');
    item.className = 'conv-item';
    const isActive = highlightSessionId ? conv.session_id === highlightSessionId : i === 0;
    if (isActive) item.classList.add('active');
    const previewText = escapeHtml((conv.messages[0]?.user || 'Conversation').substring(0, 38));
    const labelText   = escapeHtml(conv.label || conv.date || conv.session_id);
    const sid         = escapeHtml(conv.session_id || ('date:' + conv.date));
    item.innerHTML = `
      <div class="conv-dot">💬</div>
      <div class="conv-meta" style="flex:1;min-width:0;">
        <div class="conv-date">${labelText}</div>
        <div class="conv-preview">${previewText}…</div>
      </div>
      <div style="display:flex;align-items:center;gap:6px;">
        <div class="conv-count">${conv.messages.length}</div>
        <button class="conv-delete-btn" title="Delete conversation"
          onclick="deleteConversation(event,'${sid}',this)">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="3 6 5 6 21 6"/>
            <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
            <path d="M10 11v6M14 11v6"/><path d="M9 6V4h6v2"/>
          </svg>
        </button>
      </div>`;
    item.addEventListener('click', () => loadConversation(conv, item));
    list.appendChild(item);
  });
}

function loadConversation(conv, clickedEl) {
  document.querySelectorAll('.conv-item').forEach(el => el.classList.remove('active'));
  clickedEl.classList.add('active');
  currentSessionId = conv.session_id || String(Date.now());
  activeSessionEl  = conv.session_id;
  const wrap = document.getElementById('messages');
  wrap.innerHTML = '';
  conv.messages.forEach(m => { addMessage('user', m.user, m.timestamp); addMessage('arjun', m.arjun, m.timestamp); });
  scrollBottom();
  if (window.innerWidth <= 768) document.getElementById('sidebar').classList.remove('open');
}

async function deleteConversation(event, date, btnEl) {
  event.stopPropagation();
  if (!confirm('Delete this conversation?\nThis cannot be undone.')) return;
  allHistory = allHistory.filter(g => g.session_id !== date);
  renderConvList();
  if (activeSessionEl === date || currentSessionId === date) newChat();
  try {
    const res  = await fetch('/api/conversations/' + encodeURIComponent(date), { method: 'DELETE' });
    const data = await res.json();
    if (!data.success) { console.error('Delete failed:', data.error); await loadHistory(); }
  } catch (e) { console.error('Delete error:', e); await loadHistory(); }
}

// ── Message sending ───────────────────────────────────────────────────────────
function sendSuggestion(text) {
  document.getElementById('user-input').value = text;
  sendMessage();
}

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 140) + 'px';
}

async function sendMessage() {
  const input = document.getElementById('user-input');
  const msg   = input.value.trim();
  if (!msg || isTyping) return;

  const intro = document.getElementById('intro-section');
  if (intro) intro.style.display = 'none';

  addMessage('user', msg);
  input.value = ''; input.style.height = 'auto';
  isTyping = true;
  document.getElementById('send-btn').disabled = true;
  document.getElementById('arjun-status-text').textContent = 'Contemplating…';
  const typingEl = addTyping();

  try {
    const res = await fetch('/api/chat', {
      method : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body   : JSON.stringify({ message: msg, session_id: currentSessionId, language: currentLang }),
    });

    if (res.status === 401) {
      typingEl.remove();
      addMessage('arjun', 'Your session has expired. Please log in again 🙏');
      setTimeout(() => { window.location.href = '/login'; }, 2500);
      return;
    }

    const data  = await res.json();
    typingEl.remove();
    const reply = data.reply || 'Something went wrong.';
    addMessage('arjun', reply);
    speak(reply);
    if (res.ok) syncLocalHistory(msg, reply);
  } catch (_) {
    typingEl.remove();
    addMessage('arjun', 'The connection to Kurukshetra was lost. Please try again 🙏');
  }

  isTyping = false;
  document.getElementById('send-btn').disabled = false;
  document.getElementById('arjun-status-text').textContent = 'Awaiting your question';
  scrollBottom();
}

// ── Voice input ───────────────────────────────────────────────────────────────
function startVoice() {
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRec) { alert('Voice input not supported in this browser. Try Chrome.'); return; }
  const btn = document.getElementById('voiceBtn');
  const rec = new SpeechRec();
  rec.lang           = (LANGUAGES[currentLang] || LANGUAGES['en']).srLang;
  rec.interimResults = false;
  rec.onstart  = () => btn.classList.add('listening');
  rec.onend    = () => btn.classList.remove('listening');
  rec.onresult = (e) => {
    const text = e.results[0][0].transcript;
    document.getElementById('user-input').value = text;
    autoResize(document.getElementById('user-input'));
    sendMessage();
  };
  rec.onerror = (e) => {
    btn.classList.remove('listening');
    if (e.error !== 'no-speech') alert('Voice recognition failed. Please try again.');
  };
  rec.start();
}

// ── Voice output ──────────────────────────────────────────────────────────────
function speak(text) {
  if (!voiceEnabled || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const cfg = LANGUAGES[currentLang] || LANGUAGES['en'];
  let spokenText = text;
  if (currentLang === 'en') spokenText = text.replace(/[\u0900-\u097F]+/g, '').replace(/\s+/g, ' ').trim();
  if (!spokenText) return;

  const utt  = new SpeechSynthesisUtterance(spokenText);
  utt.lang   = cfg.ttsLang;
  utt.volume = 1;
  utt.rate   = TTS_RATE[currentLang] || 0.82;
  utt.pitch  = (currentLang === 'ja' || currentLang === 'zh') ? 0.1 : 0.05;

  const voices = window.speechSynthesis.getVoices();
  let selected = null;
  for (const name of (cfg.voices || [])) { selected = voices.find(v => v.name.includes(name)); if (selected) break; }
  if (!selected) selected = voices.find(v => v.lang === cfg.ttsLang);
  if (!selected) { const prefix = cfg.ttsLang.split('-')[0]; selected = voices.find(v => v.lang.startsWith(prefix)); }
  if (selected) utt.voice = selected;

  utt.onstart = () => { document.getElementById('arjun-status-text').textContent = 'Speaking…'; };
  utt.onend   = () => { document.getElementById('arjun-status-text').textContent = 'Awaiting your question'; };
  window.speechSynthesis.speak(utt);
}

// ── DOM helpers ───────────────────────────────────────────────────────────────
function addMessage(role, text, isoTimestamp) {
  const isArjun = role === 'arjun';
  const _d  = isoTimestamp ? new Date(isoTimestamp) : new Date();
  const d   = (_d instanceof Date && !isNaN(_d)) ? _d : new Date();
  const time = d.toLocaleTimeString([], { hour:'2-digit', minute:'2-digit' });
  let safeText = escapeHtml(text);
  if (isArjun) safeText = safeText.replace(/([\u0900-\u097F][^\n<]*)/g, '<div class="shloka-box">$1</div>');
  const msgDiv = document.getElementById('messages');
  const div    = document.createElement('div');
  div.className = 'message ' + role;
  div.innerHTML = `
    <div class="msg-avatar ${role}">${isArjun ? '🏹' : escapeHtml(userName.charAt(0).toUpperCase())}</div>
    <div class="msg-content">
      <div class="msg-bubble">${safeText}</div>
      <div class="msg-time">${isArjun ? 'Arjun' : 'You'} · ${escapeHtml(time)}</div>
    </div>`;
  msgDiv.appendChild(div);
  scrollBottom();
}

function addTyping() {
  const wrap = document.getElementById('messages');
  const div  = document.createElement('div');
  div.className = 'message arjun';
  div.innerHTML = `<div class="msg-avatar arjun">🏹</div>
    <div class="msg-content"><div class="typing-indicator">
      <div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>
    </div></div>`;
  wrap.appendChild(div);
  scrollBottom();
  return div;
}

function scrollBottom() {
  const wrap = document.getElementById('messages');
  wrap.scrollTop = wrap.scrollHeight;
}

async function doLogout() {
  try { await fetch('/logout', { method: 'POST' }); } catch (_) {}
  window.location.href = '/';
}

// ── Three.js background (initialised after script loads) ─────────────────────
function initThreeScene() {
  if (typeof THREE === 'undefined') return;
  const canvas   = document.getElementById('bg-canvas');
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setClearColor(0x06030f, 1);

  const scene  = new THREE.Scene();
  scene.fog    = new THREE.FogExp2(0x06030f, 0.008);
  const camera = new THREE.PerspectiveCamera(70, window.innerWidth / window.innerHeight, 0.1, 500);
  camera.position.set(0, 0, 60);

  scene.add(new THREE.AmbientLight(0x1a0a2e, 2));
  const goldLight   = new THREE.PointLight(0xd4a017, 3, 120); goldLight.position.set(0, 0, 20); scene.add(goldLight);
  const purpleLight = new THREE.PointLight(0x6b21a8, 2, 100); purpleLight.position.set(-30, 20, -10); scene.add(purpleLight);

  const mkTorus = (r, tube, segs, col, op, z) => {
    const m = new THREE.Mesh(new THREE.TorusGeometry(r, tube, 6, segs),
      new THREE.MeshBasicMaterial({ color: col, wireframe: true, transparent: true, opacity: op }));
    m.position.z = z; return m;
  };
  const chakra    = mkTorus(22, 0.4, 64, 0xd4a017, 0.35, -30);
  const innerRing = mkTorus(12, 0.3, 48, 0xe8b84b, 0.25, -25);
  const outerRing = mkTorus(34, 0.25, 80, 0xa07010, 0.15, -40);
  scene.add(chakra, innerRing, outerRing);

  const spokeMat   = new THREE.MeshBasicMaterial({ color: 0xd4a017, transparent: true, opacity: 0.18 });
  const spokeGroup = new THREE.Group(); spokeGroup.position.z = -28;
  for (let i = 0; i < 8; i++) {
    const s = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.1, 20, 4), spokeMat);
    s.rotation.z = (i / 8) * Math.PI; spokeGroup.add(s);
  }
  scene.add(spokeGroup);

  const N = 700, pos = new Float32Array(N*3), vel = new Float32Array(N*3), col = new Float32Array(N*3);
  for (let i = 0; i < N; i++) {
    const i3 = i*3;
    pos[i3]=(Math.random()-0.5)*160; pos[i3+1]=(Math.random()-0.5)*100; pos[i3+2]=(Math.random()-0.5)*80-20;
    vel[i3]=(Math.random()-0.5)*0.015; vel[i3+1]=Math.random()*0.02+0.005; vel[i3+2]=(Math.random()-0.5)*0.01;
    const t = Math.random();
    if (t<0.5)      { col[i3]=0.85+Math.random()*0.15; col[i3+1]=0.55+Math.random()*0.3; col[i3+2]=0.05+Math.random()*0.2; }
    else if (t<0.8) { col[i3]=0.9+Math.random()*0.1;  col[i3+1]=0.8+Math.random()*0.2;  col[i3+2]=0.3+Math.random()*0.3; }
    else             { col[i3]=0.95; col[i3+1]=0.95; col[i3+2]=0.95; }
  }
  const pGeo = new THREE.BufferGeometry();
  pGeo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  pGeo.setAttribute('color',    new THREE.BufferAttribute(col, 3));
  const particles = new THREE.Points(pGeo, new THREE.PointsMaterial({
    size:0.8, vertexColors:true, transparent:true, opacity:0.85,
    sizeAttenuation:true, blending:THREE.AdditiveBlending, depthWrite:false,
  }));
  scene.add(particles);

  const stPos = new Float32Array(300*3);
  for (let i=0;i<300;i++) { stPos[i*3]=(Math.random()-0.5)*300; stPos[i*3+1]=(Math.random()-0.5)*200; stPos[i*3+2]=-60-Math.random()*100; }
  const stGeo = new THREE.BufferGeometry(); stGeo.setAttribute('position', new THREE.BufferAttribute(stPos,3));
  scene.add(new THREE.Points(stGeo, new THREE.PointsMaterial({ size:0.3, color:0xffffff, transparent:true, opacity:0.5, sizeAttenuation:true, blending:THREE.AdditiveBlending, depthWrite:false })));

  let frame = 0;
  const posAttr = pGeo.attributes.position;
  function animate() {
    requestAnimationFrame(animate); frame++;
    chakra.rotation.z+=0.0025; chakra.rotation.x+=0.0008;
    innerRing.rotation.z-=0.004; innerRing.rotation.y+=0.001;
    spokeGroup.rotation.z+=0.0025;
    outerRing.rotation.z-=0.001; outerRing.rotation.x+=0.0005;
    goldLight.intensity = 2.5+Math.sin(frame*0.02)*1.0;
    for (let i=0;i<N;i++) {
      const i3=i*3;
      posAttr.array[i3]+=vel[i3]; posAttr.array[i3+1]+=vel[i3+1]; posAttr.array[i3+2]+=vel[i3+2];
      if (posAttr.array[i3+1]>50)  posAttr.array[i3+1]=-50;
      if (posAttr.array[i3]>80)    posAttr.array[i3]=-80;
      if (posAttr.array[i3]<-80)   posAttr.array[i3]=80;
    }
    posAttr.needsUpdate = true;
    camera.position.x = Math.sin(frame*0.003)*3; camera.position.y=Math.cos(frame*0.002)*2; camera.lookAt(0,0,0);
    renderer.render(scene, camera);
  }
  animate();
  window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth/window.innerHeight; camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });
}
