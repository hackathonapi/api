const inputEl      = document.getElementById("input");
const submitBtn    = document.getElementById("submit");
const submitLabel  = document.getElementById("submit-label");
const statusEl     = document.getElementById("status");
const resultsEl    = document.getElementById("results");

// Stats
const statWords  = document.getElementById("stat-words");
const statSource = document.getElementById("stat-source");

// Metric cards
const metricBias  = document.getElementById("metric-bias");
const metricCred  = document.getElementById("metric-credibility");
const metricScam  = document.getElementById("metric-scam");
const biasValue   = document.getElementById("bias-value");
const credValue   = document.getElementById("credibility-value");
const scamValue   = document.getElementById("scam-value");
const biasReason  = document.getElementById("bias-reason");
const credReason  = document.getElementById("credibility-reason");
const scamReason  = document.getElementById("scam-reason");

// PDF
const pdfEmpty    = document.getElementById("pdf-empty");
const pdfFrame    = document.getElementById("pdf-frame");
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

/**
 * Apply state to a metric card.
 * state: "good" | "warn" | "bad" | "neutral"
 */
function applyMetric(card, valueEl, reasonEl, label, reason, state) {
  const dot = card?.querySelector(".mc-dot");
  if (dot) dot.dataset.state = state;
  if (card) card.dataset.active = state === "neutral" ? "" : state;
  if (valueEl) valueEl.textContent = label;
  if (reasonEl && reason) reasonEl.textContent = reason;
}

// ─────────────────────────────────────────────
// Render results
// ─────────────────────────────────────────────

function showResults(data) {

  // Stats
  if (statWords)  statWords.textContent  = data.word_count != null ? Number(data.word_count).toLocaleString() : "—";
  if (statSource) statSource.textContent = data.source ?? "—";

  // Bias metric
  const bias = data.bias ?? null;
  if (bias != null) {
    const s = /none|low/i.test(bias) ? "good" : /moderate|medium/i.test(bias) ? "warn" : "bad";
    const r = data.bias_reason ?? `Bias level assessed as "${bias}".`;
    applyMetric(metricBias, biasValue, biasReason, bias, r, s);
  } else {
    applyMetric(metricBias, biasValue, biasReason, "—",
      "Bias analysis not returned by the API yet.", "neutral");
  }

  // Credibility metric
  const cred = data.credibility ?? null;
  if (cred != null) {
    const s = /high|credible|reliable/i.test(cred) ? "good" : /moderate|mixed/i.test(cred) ? "warn" : "bad";
    const r = data.credibility_reason ?? `Source credibility assessed as "${cred}".`;
    applyMetric(metricCred, credValue, credReason, cred, r, s);
  } else {
    applyMetric(metricCred, credValue, credReason, "—",
      "Credibility analysis not returned by the API yet.", "neutral");
  }

  // Scam metric
  const scam = data.scam_risk ?? data.scam ?? null;
  if (scam != null) {
    const s = /none|low/i.test(scam) ? "good" : /moderate|medium/i.test(scam) ? "warn" : "bad";
    const r = data.scam_reason ?? `Scam risk assessed as "${scam}".`;
    applyMetric(metricScam, scamValue, scamReason, scam, r, s);
  } else {
    applyMetric(metricScam, scamValue, scamReason, "—",
      "Scam analysis not returned by the API yet.", "neutral");
  }

  // PDF viewer
  if (data.pdf_url) {
    if (pdfEmpty) pdfEmpty.hidden = true;
    if (pdfFrame) { pdfFrame.src = data.pdf_url; pdfFrame.hidden = false; }
    if (pdfDownload) { pdfDownload.href = data.pdf_url; pdfDownload.removeAttribute("aria-disabled"); }
  } else {
    if (pdfEmpty) pdfEmpty.hidden = false;
    if (pdfFrame) { pdfFrame.src = ""; pdfFrame.hidden = true; }
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
    const res = await fetch(`${window.location.origin}/extract`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input }),
    });

    const data = await res.json();
    showResults(data);
    setStatus(res.ok ? "" : `Error ${res.status}`);
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

