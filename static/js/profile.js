/**
 * profile.js — load profile data, render conversation history, handle logout.
 */

function escapeHtml(text) {
  return String(text)
    .replace(/&/g,  "&amp;")
    .replace(/</g,  "&lt;")
    .replace(/>/g,  "&gt;")
    .replace(/"/g,  "&quot;")
    .replace(/'/g,  "&#039;");
}

function toggleConv(item) {
  item.classList.toggle("expanded");
}

async function doLogout() {
  try { await fetch("/logout", { method: "POST" }); } catch (_) {}
  window.location.href = "/";
}

async function loadProfile() {
  try {
    var res  = await fetch("/api/profile");
    var data = await res.json();

    // User card
    document.getElementById("profile-avatar").textContent  = (data.name || "U").charAt(0).toUpperCase();
    document.getElementById("profile-name").textContent    = data.name  || "User";
    document.getElementById("profile-email").textContent   = data.email || "";
    document.getElementById("stat-messages").textContent   = data.total_messages || 0;
    document.getElementById("stat-sessions").textContent   = data.total_sessions || 0;

    // Conversation list
    var convs  = data.conversations || [];
    var listEl = document.getElementById("profile-conv-list");
    document.getElementById("conv-total").textContent = convs.length + " sessions";

    if (convs.length === 0) {
      listEl.innerHTML =
        '<div class="empty-state">No conversations yet. Start chatting with Arjun!</div>';
      return;
    }

    listEl.innerHTML = "";

    // Show newest first
    convs.slice().reverse().forEach(function (conv, idx) {
      var preview = (conv.messages[0] && conv.messages[0].user)
        ? escapeHtml(conv.messages[0].user.substring(0, 60))
        : "Conversation";

      var item = document.createElement("div");
      item.className = "profile-conv-item";
      item.innerHTML =
        '<div class="profile-conv-header" onclick="toggleConv(this.parentElement)">'
        +  '<div class="conv-icon">📜</div>'
        +  '<div class="conv-info">'
        +    '<div class="conv-title">' + escapeHtml(conv.label || conv.date) + '</div>'
        +    '<div class="conv-subtitle">' + preview + '…</div>'
        +  '</div>'
        +  '<div class="conv-meta">'
        +    '<span class="conv-badge">' + conv.messages.length + ' msgs</span>'
        +    '<span class="conv-expand">▼</span>'
        +  '</div>'
        + '</div>'
        + '<div class="conv-messages" id="conv-msgs-' + idx + '"></div>';

      var msgsEl = item.querySelector("#conv-msgs-" + idx);
      conv.messages.forEach(function (m) {
        msgsEl.innerHTML +=
          '<div class="mini-msg user">'
          +  '<div class="mini-avatar user">U</div>'
          +  '<div class="mini-bubble">' + escapeHtml(m.user) + '</div>'
          + '</div>'
          + '<div class="mini-msg arjun">'
          +  '<div class="mini-avatar arjun">🏹</div>'
          +  '<div class="mini-bubble">'
          +    escapeHtml(m.arjun.substring(0, 200)) + (m.arjun.length > 200 ? '…' : '')
          +  '</div>'
          + '</div>';
      });

      listEl.appendChild(item);
    });

  } catch (_) {
    document.getElementById("profile-conv-list").innerHTML =
      '<div class="error-state">Failed to load profile. Please refresh.</div>';
  }
}

loadProfile();
