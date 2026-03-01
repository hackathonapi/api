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

// Metric cards
const mcBias   = document.getElementById("metric-bias");
const mcCred   = document.getElementById("metric-credibility");
const mcScam   = document.getElementById("metric-scam");
const mcBiasValue  = document.getElementById("mc-bias-value");
const mcCredValue  = document.getElementById("mc-cred-value");
const mcScamValue  = document.getElementById("mc-scam-value");
const mcBiasReason = document.getElementById("mc-bias-reason");
const mcCredReason = document.getElementById("mc-cred-reason");
const mcScamReason = document.getElementById("mc-scam-reason");

// ─────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────

function setStatus(msg) {
  if (statusEl) statusEl.textContent = msg;
}

function applyMetric(card, valueEl, reasonEl, label, reason, state) {
  if (!card) return;
  card.dataset.active = state;
  if (valueEl) valueEl.textContent = label;
  if (reasonEl) reasonEl.textContent = reason ?? "";
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

  // Metric cards
  if (data.is_scam !== undefined) {
    const scamState = data.is_scam ? "bad" : "good";
    const scamLabel = data.is_scam ? "High" : "Low";
    applyMetric(mcScam, mcScamValue, mcScamReason, scamLabel, data.scam_notes, scamState);
  }

  if (data.is_subjective !== undefined) {
    const credState = data.is_subjective ? "warn" : "good";
    const credLabel = data.is_subjective ? "Subjective" : "Objective";
    applyMetric(mcCred, mcCredValue, mcCredReason, credLabel, data.subjective_notes, credState);
  }

  if (data.biases !== undefined) {
    const hasBias  = Array.isArray(data.biases) && data.biases.length > 0;
    const biasState = hasBias ? "warn" : "good";
    const biasLabel = hasBias ? data.biases[0] : "None detected";
    applyMetric(mcBias, mcBiasValue, mcBiasReason, biasLabel, data.bias_notes, biasState);
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
      word_count:       clearview.word_count,
      source:           clearview.source,
      pdf_url,
      audio_url,
      is_scam:          clearview.is_scam,
      is_subjective:    clearview.is_subjective,
      biases:           clearview.biases,
      scam_notes:       clearview.scam_notes,
      subjective_notes: clearview.subjective_notes,
      bias_notes:       clearview.bias_notes,
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
