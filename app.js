const inputEl      = document.getElementById("input");
const submitBtn    = document.getElementById("submit");
const submitLabel  = document.getElementById("submit-label");
const statusEl     = document.getElementById("status");
const resultsEl    = document.getElementById("results");

// Stats
const statWords  = document.getElementById("stat-words");
const statSource = document.getElementById("stat-source");

// PDF
const pdfDownload = document.getElementById("pdf-download");

// Audio
const audioEmpty    = document.getElementById("audio-empty");
const audioPlayer   = document.getElementById("audio-player");
const audioDownload = document.getElementById("audio-download");

// ─────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────

function setStatus(msg) {
  if (statusEl) statusEl.textContent = msg;
}

// ─────────────────────────────────────────────
// Render results
// ─────────────────────────────────────────────

function showResults(data) {

  // Stats
  if (statWords)  statWords.textContent  = data.word_count != null ? Number(data.word_count).toLocaleString() : "—";
  if (statSource) statSource.textContent = data.source ?? "—";

  // PDF download
  if (data.pdf_url) {
    if (pdfDownload) { pdfDownload.href = data.pdf_url; pdfDownload.removeAttribute("aria-disabled"); }
  } else {
    if (pdfDownload) { pdfDownload.setAttribute("aria-disabled", "true"); pdfDownload.href = "#"; }
  }

  // Audio
  if (data.audio_url) {
    if (audioEmpty) audioEmpty.hidden = true;
    if (audioPlayer) { audioPlayer.src = data.audio_url; audioPlayer.hidden = false; }
    if (audioDownload) { audioDownload.href = data.audio_url; audioDownload.removeAttribute("aria-disabled"); }
  } else {
    if (audioEmpty) audioEmpty.hidden = false;
    if (audioPlayer) { audioPlayer.src = ""; audioPlayer.hidden = true; }
    if (audioDownload) { audioDownload.setAttribute("aria-disabled", "true"); audioDownload.href = "#"; }
  }

  // Re-trigger stagger animations on new results
  if (resultsEl) {
    resultsEl.classList.remove("show");
    void resultsEl.offsetWidth;
    resultsEl.classList.add("show");
  }
}

// ─────────────────────────────────────────────
// API call
// ─────────────────────────────────────────────

async function runRequest() {
  const input = inputEl?.value.trim() ?? "";
  if (!input) {
    setStatus("Enter a URL or some text first.");
    inputEl?.focus();
    return;
  }

  submitBtn.disabled = true;
  if (submitLabel) submitLabel.textContent = "Analyzing…";
  setStatus("");

  try {
    const body = JSON.stringify({ input });
    const headers = { "Content-Type": "application/json" };

    const API = "https://hackathon-api-87l4.onrender.com";
    const [clearviewRes, audioRes] = await Promise.all([
      fetch(`${API}/clearview`, { method: "POST", headers, body }),
      fetch(`${API}/audio`,     { method: "POST", headers, body }),
    ]);

    const [clearview, audioBlob] = await Promise.all([
      clearviewRes.json(),
      audioRes.ok ? audioRes.blob() : Promise.resolve(null),
    ]);

    // PDF: base64 → blob URL
    let pdf_url = null;
    if (clearviewRes.ok && clearview.pdf) {
      const pdfBytes = Uint8Array.from(atob(clearview.pdf), c => c.charCodeAt(0));
      pdf_url = URL.createObjectURL(new Blob([pdfBytes], { type: "application/pdf" }));
    }

    // Audio: streaming response → blob URL
    const audio_url = audioBlob ? URL.createObjectURL(audioBlob) : null;

    showResults({
      word_count: clearview.word_count,
      source:     clearview.source,
      pdf_url,
      audio_url,
    });

    setStatus(clearviewRes.ok ? "" : `Error ${clearviewRes.status}`);
  } catch {
    setStatus("Network error — is the API running?");
  } finally {
    submitBtn.disabled = false;
    if (submitLabel) submitLabel.textContent = "Analyze";
  }
}

// ─────────────────────────────────────────────
// Events
// ─────────────────────────────────────────────

submitBtn?.addEventListener("click", runRequest);

inputEl?.addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === "Enter") runRequest();
});
