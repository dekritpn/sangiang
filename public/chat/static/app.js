// ==========================================================================
// SANGIANG CHATBOT - GEMINI CLIENT CONTROLLER
// Initiator: Yayasan Cipta Manggala Dwipa
// AI System Engineering & Translation: Divisi DigiLab CMD
// ==========================================================================

let conversation = [];
let isStreaming = false;
let currentAbortController = null;
let activeSessionId = "session_" + Date.now();

// DOM References
const appContainer = document.getElementById("app");
const sidebar = document.getElementById("sidebar");
const sidebarBackdrop = document.getElementById("sidebar-backdrop");
const btnToggleSidebar = document.getElementById("btn-toggle-sidebar");
const btnOpenSidebar = document.getElementById("btn-open-sidebar");
const btnNewChat = document.getElementById("btn-new-chat");
const btnClearChat = document.getElementById("btn-clear-chat");
const btnThemeToggle = document.getElementById("btn-theme-toggle");
const themeText = document.getElementById("theme-text");
const chatModelSelect = document.getElementById("chat-model-select");
const sidebarModelName = document.getElementById("sidebar-model-name");
const headerModelBadge = document.getElementById("header-model-badge");
const heroGreeting = document.getElementById("hero-greeting");
const messagesContainer = document.getElementById("messages-container");
const chatViewport = document.getElementById("chat-viewport");
const promptInput = document.getElementById("prompt-input");
const btnSend = document.getElementById("btn-send");
const diacriticDock = document.getElementById("diacritic-dock");
const btnToggleDiacritics = document.getElementById("btn-toggle-diacritics");
const btnDockClose = document.getElementById("btn-dock-close");
const recentChatsList = document.getElementById("recent-chats-list");

// Modal Elements
const aboutModal = document.getElementById("about-modal");
const btnAbout = document.getElementById("btn-about");
const btnModalClose = document.getElementById("btn-modal-close");
const btnModalOk = document.getElementById("btn-modal-ok");

// --------------------------------------------------------------------------
// 1. Initialization & Event Listeners
// --------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initTextareaAutoGrow();
  bindSuggestionCards();
  bindDiacriticKeys();
  loadRecentSessions();

  const navTranslateLink = document.getElementById("nav-translate-link");
  if (navTranslateLink) {
    const host = window.location.hostname;
    if (host === "localhost" || host === "127.0.0.1") {
      navTranslateLink.href = "http://localhost:8000";
    } else if (host.endsWith(".sangihe.org") || host === "sangihe.org") {
      navTranslateLink.href = "https://translate.sangihe.org";
    } else {
      navTranslateLink.href = "/";
    }
  }
});

// Sidebar Toggle (Responsive: Mobile Drawer vs Desktop Collapsible)
function isMobileViewport() {
  return window.matchMedia("(max-width: 768px)").matches;
}

function openMobileSidebar() {
  sidebar.classList.add("mobile-open");
  sidebarBackdrop?.classList.add("active");
}

function closeMobileSidebar() {
  sidebar.classList.remove("mobile-open");
  sidebarBackdrop?.classList.remove("active");
}

btnToggleSidebar.addEventListener("click", () => {
  if (isMobileViewport()) {
    closeMobileSidebar();
  } else {
    sidebar.classList.toggle("collapsed");
  }
});

btnOpenSidebar?.addEventListener("click", () => {
  if (isMobileViewport()) {
    openMobileSidebar();
  } else {
    sidebar.classList.toggle("collapsed");
  }
});

sidebarBackdrop?.addEventListener("click", () => {
  closeMobileSidebar();
});

// New Chat
btnNewChat.addEventListener("click", () => {
  if (isStreaming) stopStreaming();
  startNewChat();
  if (isMobileViewport()) closeMobileSidebar();
});

// Clear Chat
btnClearChat.addEventListener("click", () => {
  if (confirm("Bersihkan seluruh riwayat percakapan di sesi ini?")) {
    if (isStreaming) stopStreaming();
    conversation = [];
    messagesContainer.innerHTML = "";
    heroGreeting.style.display = "flex";
    saveActiveSession();
  }
});

// About Modal
btnAbout.addEventListener("click", () => {
  if (isMobileViewport()) closeMobileSidebar();
  aboutModal.style.display = "flex";
});
btnModalClose.addEventListener("click", () => {
  aboutModal.style.display = "none";
});
btnModalOk.addEventListener("click", () => {
  aboutModal.style.display = "none";
});
aboutModal.addEventListener("click", (e) => {
  if (e.target === aboutModal) aboutModal.style.display = "none";
});

// Theme Switcher
btnThemeToggle.addEventListener("click", () => {
  const isLight = document.body.classList.toggle("light-theme");
  themeText.textContent = isLight ? "Mode Gelap" : "Mode Terang";
  localStorage.setItem("sangiang_theme", isLight ? "light" : "dark");
});

function initTheme() {
  const saved = localStorage.getItem("sangiang_theme");
  if (saved === "light") {
    document.body.classList.add("light-theme");
    themeText.textContent = "Mode Gelap";
  } else {
    document.body.classList.remove("light-theme");
    themeText.textContent = "Mode Terang";
  }
}

// --------------------------------------------------------------------------
// 2. Identity Label
// --------------------------------------------------------------------------
function updateModelLabels() {
  if (sidebarModelName) sidebarModelName.textContent = "Sangiang";
  if (headerModelBadge) headerModelBadge.textContent = "Sangiang";
}

// --------------------------------------------------------------------------
// 3. Textarea Auto-Grow & Send Triggers
// --------------------------------------------------------------------------
function initTextareaAutoGrow() {
  promptInput.addEventListener("input", () => {
    promptInput.style.height = "auto";
    promptInput.style.height = Math.min(promptInput.scrollHeight, 180) + "px";
  });

  promptInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendPrompt();
    }
  });

  btnSend.addEventListener("click", () => {
    if (isStreaming) {
      stopStreaming();
    } else {
      handleSendPrompt();
    }
  });
}

function bindSuggestionCards() {
  document.querySelectorAll(".suggestion-card").forEach(card => {
    card.addEventListener("click", () => {
      const prompt = card.getAttribute("data-prompt");
      if (prompt) {
        promptInput.value = prompt;
        promptInput.dispatchEvent(new Event("input"));
        handleSendPrompt();
      }
    });
  });
}

// --------------------------------------------------------------------------
// 4. Sangihe Diacritic Insertion Toolbar
// --------------------------------------------------------------------------
btnToggleDiacritics.addEventListener("click", () => {
  const isVisible = diacriticDock.style.display === "flex";
  diacriticDock.style.display = isVisible ? "none" : "flex";
});

btnDockClose.addEventListener("click", () => {
  diacriticDock.style.display = "none";
});

function bindDiacriticKeys() {
  document.querySelectorAll(".dock-key").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const char = btn.getAttribute("data-char");
      insertCharToPrompt(char);
    });
  });
}

function insertCharToPrompt(char) {
  const start = promptInput.selectionStart || promptInput.value.length;
  const end = promptInput.selectionEnd || promptInput.value.length;
  const currentVal = promptInput.value;

  promptInput.value = currentVal.substring(0, start) + char + currentVal.substring(end);
  promptInput.focus();
  const nextPos = start + char.length;
  promptInput.setSelectionRange(nextPos, nextPos);
  promptInput.dispatchEvent(new Event("input"));
}

// --------------------------------------------------------------------------
// 5. Send Prompt & SSE Streaming Controller
// --------------------------------------------------------------------------
async function handleSendPrompt() {
  const text = promptInput.value.trim();
  if (!text || isStreaming) return;

  // Hide hero greeting on first message
  heroGreeting.style.display = "none";

  // Append user message
  appendMessage("user", text);
  conversation.push({ role: "user", content: text });

  // Clear prompt
  promptInput.value = "";
  promptInput.style.height = "auto";

  // Create assistant placeholder bubble
  const assistantMsgObj = appendMessage("assistant", "", true);
  
  // Set streaming status
  setStreamingState(true);
  currentAbortController = new AbortController();

  let fullResponseText = "";

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages: conversation,
        stream: true,
        temperature: 0.4
      }),
      signal: currentAbortController.signal,
    });

    if (!response.ok) {
      throw new Error(`Server returned error HTTP ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n\n");
      buffer = lines.pop(); // keep last incomplete chunk

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith("data:")) continue;
        const jsonStr = trimmed.substring(5).trim();
        if (!jsonStr) continue;

        try {
          const parsed = JSON.parse(jsonStr);
          if (parsed.error) {
            fullResponseText += `\n\n> ⚠️ *${parsed.error}*`;
          } else if (parsed.chunk) {
            fullResponseText += parsed.chunk;
          }

          // Update UI live
          updateMessageContent(assistantMsgObj.bubbleEl, fullResponseText, true);
          scrollToBottom();

          if (parsed.done) break;
        } catch (jsonErr) {
          // ignore partial JSON parse error
        }
      }
    }
  } catch (err) {
    if (err.name === "AbortError") {
      fullResponseText += "\n\n*(Generasi dihentikan oleh pengguna)*";
    } else {
      fullResponseText += `\n\n> ⚠️ **Error:** Gagal terhubung dengan Sangiang (${err.message}).`;
    }
    updateMessageContent(assistantMsgObj.bubbleEl, fullResponseText, false);
  } finally {
    setStreamingState(false);
    updateMessageContent(assistantMsgObj.bubbleEl, fullResponseText, false);
    conversation.push({ role: "assistant", content: fullResponseText });
    saveActiveSession();
    scrollToBottom();
  }
}

function stopStreaming() {
  if (currentAbortController) {
    currentAbortController.abort();
    currentAbortController = null;
  }
  setStreamingState(false);
}

function setStreamingState(streaming) {
  isStreaming = streaming;
  const sendIcon = btnSend.querySelector(".send-icon");
  const stopIcon = btnSend.querySelector(".stop-icon");

  if (streaming) {
    sendIcon.style.display = "none";
    stopIcon.style.display = "block";
    btnSend.title = "Hentikan pembuatan respons";
    btnSend.style.background = "#ef4444";
  } else {
    sendIcon.style.display = "block";
    stopIcon.style.display = "none";
    btnSend.title = "Kirim pesan";
    btnSend.style.background = "var(--aurora-gradient)";
  }
}

// --------------------------------------------------------------------------
// 6. Message Rendering & Actions
// --------------------------------------------------------------------------
function appendMessage(role, content, isTemporaryStreaming = false) {
  const row = document.createElement("div");
  row.className = `message-row ${role}`;

  const avatar = document.createElement("div");
  avatar.className = `message-avatar ${role}-avatar`;
  avatar.innerHTML = role === "user" ? "U" : `<img src="/chat/static/sangiang.jpeg" alt="Sangiang" class="sangiang-avatar-img">`;

  const wrapper = document.createElement("div");
  wrapper.className = "message-bubble-wrapper";

  const bubble = document.createElement("div");
  bubble.className = "message-bubble";

  updateMessageContent(bubble, content, isTemporaryStreaming);
  wrapper.appendChild(bubble);

  // Add action buttons for assistant messages
  if (role === "assistant") {
    const actions = document.createElement("div");
    actions.className = "message-actions";
    actions.innerHTML = `
      <button class="action-btn btn-copy" title="Salin teks">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
        </svg>
      </button>
      <button class="action-btn btn-speak" title="Dengarkan (TTS)">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
          <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>
        </svg>
      </button>
      <button class="action-btn btn-retry" title="Buat ulang respons">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="23 4 23 10 17 10"></polyline>
          <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
        </svg>
      </button>
    `;

    // Bind action events
    const copyBtn = actions.querySelector(".btn-copy");
    copyBtn.addEventListener("click", () => {
      const rawText = bubble.innerText;
      navigator.clipboard.writeText(rawText);
      copyBtn.classList.add("copied");
      copyBtn.innerHTML = `
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.5">
          <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
      `;
      setTimeout(() => {
        copyBtn.classList.remove("copied");
        copyBtn.innerHTML = `
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
          </svg>
        `;
      }, 2000);
    });

    const speakBtn = actions.querySelector(".btn-speak");
    speakBtn.addEventListener("click", () => {
      speakText(bubble.innerText);
    });

    const retryBtn = actions.querySelector(".btn-retry");
    retryBtn.addEventListener("click", () => {
      if (isStreaming) return;
      // Remove last assistant message
      row.remove();
      conversation.pop();
      // Trigger regeneration
      regenerateLastResponse();
    });

    wrapper.appendChild(actions);
  }

  if (role === "assistant") {
    row.appendChild(avatar);
    row.appendChild(wrapper);
  } else {
    row.appendChild(wrapper);
    row.appendChild(avatar);
  }

  messagesContainer.appendChild(row);
  scrollToBottom();

  return { rowEl: row, bubbleEl: bubble };
}

function updateMessageContent(bubbleEl, rawContent, isStreamingNow) {
  let renderedHtml = "";
  if (typeof marked !== "undefined" && marked.parse) {
    try {
      renderedHtml = marked.parse(rawContent || "");
    } catch {
      renderedHtml = fallbackMarkdown(rawContent || "");
    }
  } else {
    renderedHtml = fallbackMarkdown(rawContent || "");
  }

  if (isStreamingNow) {
    renderedHtml += `<span class="streaming-cursor"></span>`;
  }

  bubbleEl.innerHTML = renderedHtml;

  // Apply code highlighting if available
  if (typeof hljs !== "undefined" && !isStreamingNow) {
    bubbleEl.querySelectorAll("pre code").forEach(block => {
      hljs.highlightElement(block);
    });
  }
}

function fallbackMarkdown(text) {
  let out = escapeHtml(text)
    .replace(/\n\n/g, "<p></p>")
    .replace(/\n/g, "<br>")
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/`(.*?)`/g, "<code>$1</code>");
  return `<p>${out}</p>`;
}

function scrollToBottom() {
  chatViewport.scrollTop = chatViewport.scrollHeight;
}

function speakText(text) {
  if (!("speechSynthesis" in window)) {
    alert("Peramban Anda tidak mendukung Text-to-Speech.");
    return;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "id-ID";
  utterance.rate = 1.0;
  window.speechSynthesis.speak(utterance);
}

async function regenerateLastResponse() {
  if (conversation.length === 0) return;
  const assistantMsgObj = appendMessage("assistant", "", true);
  setStreamingState(true);
  currentAbortController = new AbortController();

  let fullResponseText = "";

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages: conversation,
        stream: true,
        temperature: 0.4
      }),
      signal: currentAbortController.signal,
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n\n");
      buffer = lines.pop();

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith("data:")) continue;
        const jsonStr = trimmed.substring(5).trim();
        if (!jsonStr) continue;

        try {
          const parsed = JSON.parse(jsonStr);
          if (parsed.chunk) fullResponseText += parsed.chunk;
          updateMessageContent(assistantMsgObj.bubbleEl, fullResponseText, true);
          scrollToBottom();
          if (parsed.done) break;
        } catch {}
      }
    }
  } catch (err) {
    fullResponseText += `\n\n> ⚠️ Error saat regenerasi: ${err.message}`;
  } finally {
    setStreamingState(false);
    updateMessageContent(assistantMsgObj.bubbleEl, fullResponseText, false);
    conversation.push({ role: "assistant", content: fullResponseText });
    saveActiveSession();
    scrollToBottom();
  }
}

// --------------------------------------------------------------------------
// 7. Recent Sessions Management (LocalStorage)
// --------------------------------------------------------------------------
function startNewChat() {
  activeSessionId = "session_" + Date.now();
  conversation = [];
  messagesContainer.innerHTML = "";
  heroGreeting.style.display = "flex";
  promptInput.focus();
  loadRecentSessions();
}

function saveActiveSession() {
  if (conversation.length === 0) return;
  const firstUserMsg = conversation.find(m => m.role === "user");
  const title = firstUserMsg ? firstUserMsg.content.substring(0, 32) + "..." : "Percakapan Baru";

  const sessionData = {
    id: activeSessionId,
    title: title,
    timestamp: Date.now(),
    conversation: conversation,
  };

  try {
    const sessions = JSON.parse(localStorage.getItem("sangiang_sessions") || "{}");
    sessions[activeSessionId] = sessionData;
    localStorage.setItem("sangiang_sessions", JSON.stringify(sessions));
    loadRecentSessions();
  } catch (e) {
    console.warn("Gagal menyimpan sesi:", e);
  }
}

function loadRecentSessions() {
  try {
    const sessions = JSON.parse(localStorage.getItem("sangiang_sessions") || "{}");
    const list = Object.values(sessions).sort((a, b) => b.timestamp - a.timestamp);

    if (list.length === 0) {
      recentChatsList.innerHTML = `
        <div class="recent-chat-item active" data-id="${activeSessionId}">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
          <span class="chat-title">Percakapan Baru</span>
        </div>
      `;
      return;
    }

    recentChatsList.innerHTML = list.map(s => {
      const isActive = (s.id === activeSessionId) ? "active" : "";
      return `
        <div class="recent-chat-item ${isActive}" data-id="${s.id}">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
          <span class="chat-title">${escapeHtml(s.title)}</span>
        </div>
      `;
    }).join("");

    // Bind click to switch session
    recentChatsList.querySelectorAll(".recent-chat-item").forEach(item => {
      item.addEventListener("click", () => {
        const id = item.getAttribute("data-id");
        switchSession(id);
        if (isMobileViewport()) closeMobileSidebar();
      });
    });
  } catch (e) {
    console.warn("Gagal memuat sesi riwayat:", e);
  }
}

function switchSession(id) {
  try {
    const sessions = JSON.parse(localStorage.getItem("sangiang_sessions") || "{}");
    const target = sessions[id];
    if (!target) return;

    if (isStreaming) stopStreaming();

    activeSessionId = target.id;
    conversation = target.conversation || [];

    messagesContainer.innerHTML = "";
    if (conversation.length === 0) {
      heroGreeting.style.display = "flex";
    } else {
      heroGreeting.style.display = "none";
      for (const msg of conversation) {
        appendMessage(msg.role, msg.content, false);
      }
    }
    loadRecentSessions();
  } catch (e) {
    console.warn("Gagal beralih sesi:", e);
  }
}

// --------------------------------------------------------------------------
// 8. Helper Utilities
// --------------------------------------------------------------------------
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
