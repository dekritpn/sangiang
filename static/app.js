// Sangihe Translation Engine Frontend Controller

let currentDirection = "sangihe_to_id";
let lastTranslatedInput = "";
let lastMachineTranslation = "";

// DOM Elements
const inputTextArea = document.getElementById("input-text");
const outputTextArea = document.getElementById("output-text");
const feedbackPanel = document.getElementById("feedback-panel");
const feedbackPromptRow = document.getElementById("feedback-prompt-row");
const feedbackCorrectionBox = document.getElementById("feedback-correction-box");
const feedbackCorrectionInput = document.getElementById("feedback-correction-input");
const feedbackStatusMsg = document.getElementById("feedback-status-msg");
const btnFeedbackGood = document.getElementById("btn-feedback-good");
const btnFeedbackEdit = document.getElementById("btn-feedback-edit");
const btnFeedbackCancel = document.getElementById("btn-feedback-cancel");
const btnFeedbackSubmit = document.getElementById("btn-feedback-submit");
const btnTranslate = document.getElementById("btn-translate");
const btnLabel = document.getElementById("btn-label");
const btnSpinner = document.getElementById("btn-spinner");
const btnSwapLang = document.getElementById("btn-swap-lang");
const btnClearInput = document.getElementById("btn-clear-input");
const btnCopyOutput = document.getElementById("btn-copy-output");
const inputCharCount = document.getElementById("input-char-count");
const latencyInfo = document.getElementById("latency-info");
const diacriticBadge = document.getElementById("diacritic-badge");
const sourceLangLabel = document.getElementById("source-lang-label");
const targetLangLabel = document.getElementById("target-lang-label");
const inputBoxTitle = document.getElementById("input-box-title");
const outputBoxTitle = document.getElementById("output-box-title");
const diacriticToolbar = document.getElementById("diacritic-toolbar");

// Inspector Elements
const lexicalResults = document.getElementById("lexical-results");
const parallelResults = document.getElementById("parallel-results");
const countLexical = document.getElementById("count-lexical");
const countParallel = document.getElementById("count-parallel");

// Tab switching
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
    btn.classList.add("active");
    const targetId = btn.getAttribute("data-tab");
    document.getElementById(targetId)?.classList.add("active");
  });
});

// Dynamic cross-subdomain link for Sangiang Chatbot (localhost vs sangihe.org vs Cloudflare Pages)
const navChatbotLink = document.getElementById("nav-chatbot-link");
if (navChatbotLink) {
  const host = window.location.hostname;
  if (host === "localhost" || host === "127.0.0.1") {
    navChatbotLink.href = "http://localhost:2026";
  } else if (host.endsWith(".sangihe.org") || host === "sangihe.org") {
    navChatbotLink.href = "https://chat.sangihe.org";
  } else {
    navChatbotLink.href = "/chat/";
  }
}

// Direction swap
btnSwapLang.addEventListener("click", () => {
  if (currentDirection === "sangihe_to_id") {
    setDirection("id_to_sangihe");
  } else {
    setDirection("sangihe_to_id");
  }
});

function setDirection(dir) {
  currentDirection = dir;
  if (dir === "sangihe_to_id") {
    sourceLangLabel.textContent = "Bahasa Sangihe";
    targetLangLabel.textContent = "Bahasa Indonesia";
    inputBoxTitle.textContent = "Input Teks Sangihe";
    outputBoxTitle.textContent = "Hasil Terjemahan Bahasa Indonesia";
    diacriticToolbar.style.display = "flex";
  } else {
    sourceLangLabel.textContent = "Bahasa Indonesia";
    targetLangLabel.textContent = "Bahasa Sangihe";
    inputBoxTitle.textContent = "Input Teks Indonesia";
    outputBoxTitle.textContent = "Hasil Terjemahan Sangihe (Berdiakritik)";
    diacriticToolbar.style.display = "none";
  }
}

// Diacritic chips insert at cursor
document.querySelectorAll(".dia-chip").forEach(chip => {
  chip.addEventListener("click", () => {
    const char = chip.getAttribute("data-char");
    insertAtCursor(inputTextArea, char);
    updateCharCount();
  });
});

function insertAtCursor(textarea, text) {
  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const val = textarea.value;
  textarea.value = val.substring(0, start) + text + val.substring(end);
  textarea.selectionStart = textarea.selectionEnd = start + text.length;
  textarea.focus();
}

// Char count
inputTextArea.addEventListener("input", updateCharCount);
function updateCharCount() {
  inputCharCount.textContent = `${inputTextArea.value.length} karakter`;
}

// Clear input
btnClearInput.addEventListener("click", () => {
  inputTextArea.value = "";
  updateCharCount();
  inputTextArea.focus();
});

// Copy output
btnCopyOutput.addEventListener("click", async () => {
  const text = outputTextArea.textContent.trim();
  if (text && !text.includes("Hasil terjemahan")) {
    await navigator.clipboard.writeText(text);
    const origHTML = btnCopyOutput.innerHTML;
    btnCopyOutput.innerHTML = `✓ Tersalin!`;
    setTimeout(() => { btnCopyOutput.innerHTML = origHTML; }, 2000);
  }
});

// Sample Pills
document.querySelectorAll(".pill-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    const text = btn.getAttribute("data-text");
    const dir = btn.getAttribute("data-dir");
    if (dir) setDirection(dir);
    inputTextArea.value = text;
    updateCharCount();
    doTranslate();
  });
});

// Translation action
btnTranslate.addEventListener("click", doTranslate);

inputTextArea.addEventListener("keydown", (e) => {
  if (e.ctrlKey && e.key === "Enter") {
    e.preventDefault();
    doTranslate();
  }
});

async function doTranslate() {
  const text = inputTextArea.value.trim();
  if (!text) return;

  setLoading(true);
  diacriticBadge.style.display = "none";
  if (feedbackPanel) feedbackPanel.style.display = "none";
  outputTextArea.innerHTML = `<span class="output-placeholder">Menganalisis leksikon & menerjemahkan bersama Sangiang...</span>`;

  try {
    const resp = await fetch("/v1/translate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: text,
        direction: currentDirection,
        temperature: 0.2,
      }),
    });

    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || "Terjadi kesalahan pada translation engine.");
    }

    const data = await resp.json();
    outputTextArea.textContent = data.translated_text;
    lastTranslatedInput = data.input_text || text;
    lastMachineTranslation = data.translated_text || "";

    // Show feedback panel for this translation
    if (feedbackPanel) {
      feedbackPanel.style.display = "block";
      feedbackPromptRow.style.display = "flex";
      feedbackCorrectionBox.style.display = "none";
      feedbackStatusMsg.style.display = "none";
      feedbackCorrectionInput.value = lastMachineTranslation;
    }

    if (data.diacritics_restored) {
      diacriticBadge.style.display = "inline-block";
    }

    latencyInfo.textContent = `Waktu: ${data.elapsed_ms.toFixed(0)} ms • Sangiang`;

    // Render Inspector Data
    renderLexicalEntries(data.lexical_entries || []);
    renderParallelMatches(data.parallel_matches || []);

    // Also trigger word morphology for first prominent word if Sangihe
    if (currentDirection === "sangihe_to_id") {
      const words = text.split(/\s+/).filter(w => w.length > 3);
      if (words.length > 0) {
        analyzeMorphologyWord(words[0]);
      }
    }
  } catch (error) {
    outputTextArea.innerHTML = `<span style="color: var(--accent-rose);">Error: ${error.message}</span>`;
  } finally {
    setLoading(false);
  }
}

function setLoading(isLoading) {
  btnTranslate.disabled = isLoading;
  if (isLoading) {
    btnSpinner.classList.add("active");
    btnLabel.textContent = "Menerjemahkan...";
  } else {
    btnSpinner.classList.remove("active");
    btnLabel.textContent = "Terjemahkan";
  }
}

// Render Lexical entries
function renderLexicalEntries(entries) {
  countLexical.textContent = entries.length;
  if (!entries || entries.length === 0) {
    lexicalResults.innerHTML = `<div class="empty-state">Tidak ada lema yang cocok langsung di kamus Steller-Aebersold.</div>`;
    return;
  }

  lexicalResults.innerHTML = entries.map(e => `
    <div class="context-card">
      <div class="card-top">
        <div>
          <span class="lemma-title">${escapeHtml(e.lema_display)}</span>
          <span class="lemma-norm">(${escapeHtml(e.lema_normalized)})</span>
        </div>
        <span class="match-tag">${escapeHtml(e.match_source)}</span>
      </div>
      <div class="gloss-body">${escapeHtml(e.summary_gloss)}</div>
    </div>
  `).join("");
}

// Render Parallel TM matches
function renderParallelMatches(matches) {
  countParallel.textContent = matches.length;
  if (!matches || matches.length === 0) {
    parallelResults.innerHTML = `<div class="empty-state">Tidak ditemukan pasangan kalimat paralel yang relevan.</div>`;
    return;
  }

  parallelResults.innerHTML = matches.map(m => `
    <div class="parallel-card">
      <div class="parallel-meta">
        <span class="ref-pill">[${escapeHtml(m.reference_id)}] (${escapeHtml(m.source_domain)})</span>
        <span class="sim-score">Skor Kemiripan: ${(m.score * 100).toFixed(1)}%</span>
      </div>
      <div class="parallel-row">
        <span class="row-label">Sangihe</span>
        <span class="row-text">${escapeHtml(m.sangihe)}</span>
      </div>
      <div class="parallel-row">
        <span class="row-label">Indonesia</span>
        <span class="row-text">${escapeHtml(m.indonesian)}</span>
      </div>
    </div>
  `).join("");
}

// Standalone Morphology
const morphInput = document.getElementById("morph-quick-input");
const btnAnalyzeMorph = document.getElementById("btn-analyze-morph");
const morphResults = document.getElementById("morph-results");

btnAnalyzeMorph.addEventListener("click", () => {
  const word = morphInput.value.trim();
  if (word) analyzeMorphologyWord(word);
});

async function analyzeMorphologyWord(word) {
  morphResults.innerHTML = `<div class="empty-state">Menganalisis afiksasi dan akar kata...</div>`;
  try {
    const resp = await fetch("/v1/morphology/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ word: word }),
    });
    if (!resp.ok) throw new Error("Gagal menganalisis morfologi");
    const m = await resp.json();

    morphResults.innerHTML = `
      <div class="morph-grid">
        <div class="morph-item">
          <div class="morph-label">KATA DASAR / AKAR KANDIDAT</div>
          <div class="morph-val">${m.candidate_stems.join(", ") || "-"}</div>
        </div>
        <div class="morph-item">
          <div class="morph-label">AWALAN (PREFIX)</div>
          <div class="morph-val">${m.prefixes.join(", ") || "Tidak ada"}</div>
        </div>
        <div class="morph-item">
          <div class="morph-label">SISIPAN (INFIX)</div>
          <div class="morph-val">${m.infixes.join(", ") || "Tidak ada"}</div>
        </div>
        <div class="morph-item">
          <div class="morph-label">AKHIRAN / ENKLITIK</div>
          <div class="morph-val">${m.suffixes.join(", ") || "Tidak ada"}</div>
        </div>
      </div>
    `;
  } catch (err) {
    morphResults.innerHTML = `<div class="empty-state" style="color:var(--accent-rose);">${err.message}</div>`;
  }
}

// Dictionary Search
const dictInput = document.getElementById("dict-search-input");
const btnDictSearch = document.getElementById("btn-dict-search");
const dictResults = document.getElementById("dict-search-results");

btnDictSearch.addEventListener("click", doDictSearch);
dictInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") doDictSearch();
});

async function doDictSearch() {
  const query = dictInput.value.trim();
  if (!query) return;

  dictResults.innerHTML = `<div class="empty-state">Mencari di Steller-Aebersold SQLite...</div>`;
  try {
    // Determine direction heuristic: if user typed something with Sangihe diacritics or looks like Sangihe
    const direction = currentDirection === "sangihe_to_id" ? "sangihe" : "indonesian";
    const resp = await fetch("/v1/dictionary/lookup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query, direction: direction, limit: 12 }),
    });
    if (!resp.ok) throw new Error("Pencarian gagal");
    const data = await resp.json();

    if (!data.results || data.results.length === 0) {
      dictResults.innerHTML = `<div class="empty-state">Tidak ditemukan lema untuk kata kunci "${escapeHtml(query)}".</div>`;
      return;
    }

    dictResults.innerHTML = data.results.map(e => `
      <div class="context-card">
        <div class="card-top">
          <div>
            <span class="lemma-title">${escapeHtml(e.lema_display)}</span>
            <span class="lemma-norm">(${escapeHtml(e.lema_normalized)})</span>
          </div>
          <span class="match-tag">${escapeHtml(e.match_source)}</span>
        </div>
        <div class="gloss-body">${escapeHtml(e.summary_gloss)}</div>
        ${e.sublemmas && e.sublemmas.length > 0 ? `
          <div class="sublemmas-wrap">
            <strong>Sublema:</strong> ${e.sublemmas.map(s => escapeHtml(s.sublema || s.lema_display || "")).filter(Boolean).slice(0, 4).join(", ")}
          </div>
        ` : ""}
      </div>
    `).join("");
  } catch (err) {
    dictResults.innerHTML = `<div class="empty-state" style="color:var(--accent-rose);">${err.message}</div>`;
  }
}

// System Health Check
async function checkSystemHealth() {
  const statusEl = document.getElementById("system-status");
  try {
    const resp = await fetch("/health");
    if (!resp.ok) throw new Error();
    const data = await resp.json();
    const dot = statusEl.querySelector(".status-dot");
    const text = statusEl.querySelector(".status-text");

    if (data.status === "healthy") {
      dot.className = "status-dot online";
      text.textContent = `Sangiang Online • Korpus: ${data.corpus_sentences_count.toLocaleString()} kalimat`;
    } else {
      dot.className = "status-dot";
      text.textContent = `Degraded`;
    }
  } catch {
    const dot = statusEl.querySelector(".status-dot");
    const text = statusEl.querySelector(".status-text");
    dot.className = "status-dot error";
    text.textContent = "Offline";
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Initialize on page load
checkSystemHealth();

// User Feedback & Correction Handlers
if (btnFeedbackGood) {
  btnFeedbackGood.addEventListener("click", async () => {
    await sendFeedback(true, "");
  });
}

if (btnFeedbackEdit) {
  btnFeedbackEdit.addEventListener("click", () => {
    feedbackPromptRow.style.display = "none";
    feedbackCorrectionBox.style.display = "flex";
    feedbackStatusMsg.style.display = "none";
    feedbackCorrectionInput.focus();
  });
}

if (btnFeedbackCancel) {
  btnFeedbackCancel.addEventListener("click", () => {
    feedbackCorrectionBox.style.display = "none";
    feedbackPromptRow.style.display = "flex";
  });
}

if (btnFeedbackSubmit) {
  btnFeedbackSubmit.addEventListener("click", async () => {
    const corrected = feedbackCorrectionInput.value.trim();
    if (!corrected) return;
    await sendFeedback(false, corrected);
  });
}

document.querySelectorAll(".dia-chip-fb").forEach(chip => {
  chip.addEventListener("click", () => {
    const char = chip.getAttribute("data-char");
    if (feedbackCorrectionInput && char) {
      insertAtCursor(feedbackCorrectionInput, char);
    }
  });
});

async function sendFeedback(isCorrect, correctedTranslation) {
  if (!lastTranslatedInput || !lastMachineTranslation) return;
  try {
    const resp = await fetch("/v1/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        input_text: lastTranslatedInput,
        machine_translation: lastMachineTranslation,
        direction: currentDirection,
        is_correct: isCorrect,
        corrected_translation: correctedTranslation,
      }),
    });
    if (!resp.ok) throw new Error("Gagal mengirim masukan");
    const data = await resp.json();
    feedbackPromptRow.style.display = "none";
    feedbackCorrectionBox.style.display = "none";
    feedbackStatusMsg.style.display = "block";
    feedbackStatusMsg.textContent = `✓ ${data.message}`;
  } catch (err) {
    feedbackStatusMsg.style.display = "block";
    feedbackStatusMsg.textContent = `⚠️ Gagal menyimpan masukan: ${err.message}`;
  }
}
