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
    const s = data.bias_state ?? (/none/i.test(bias) ? "good" : /low|moderate/i.test(bias) ? "warn" : "bad");
    const r = data.bias_reason ?? `Bias level assessed as "${bias}".`;
    applyMetric(metricBias, biasValue, biasReason, bias, r, s);
  } else {
    applyMetric(metricBias, biasValue, biasReason, "—",
      "Bias analysis not returned by the API yet.", "neutral");
  }

  // Credibility metric
  const cred = data.credibility ?? null;
  if (cred != null) {
    const s = data.credibility_state ?? (/high/i.test(cred) ? "good" : /moderate/i.test(cred) ? "warn" : "bad");
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

    // Bias: map server list + subjectivity → clean label + state
    let biasLabel, biasState;
    if (clearview.biases?.length >= 2) {
      biasLabel = "High";     biasState = "bad";
    } else if (clearview.biases?.length === 1) {
      biasLabel = "Moderate"; biasState = "warn";
    } else if (clearview.is_subjective) {
      biasLabel = "Low";      biasState = "warn";
    } else {
      biasLabel = "None";     biasState = "good";
    }
    const biasReason = clearview.bias_notes ?? clearview.subjective_notes ?? null;

    // Scam: boolean → label
    const scamLabel  = clearview.is_scam ? "High" : "None";
    const scamReason = clearview.scam_notes ?? null;

    // Credibility: derive from scam + bias + subjectivity signals
    let credLabel, credState, credReason;
    if (clearview.is_scam) {
      credLabel = "Low"; credState = "bad";
      credReason = "Scam signals detected, which strongly reduces source credibility.";
    } else if (clearview.biases?.length > 0 && clearview.is_subjective) {
      credLabel = "Low"; credState = "bad";
      credReason = clearview.bias_notes ?? "Bias and subjective language both detected.";
    } else if (clearview.biases?.length > 0 || clearview.is_subjective) {
      credLabel = "Moderate"; credState = "warn";
      credReason = clearview.bias_notes ?? clearview.subjective_notes
        ?? "Some bias or subjectivity detected — consider seeking additional sources.";
    } else {
      credLabel = "High"; credState = "good";
      credReason = "No significant bias, subjectivity, or scam signals detected.";
    }

    showResults({
      word_count:         clearview.word_count,
      source:             clearview.source,
      bias:               biasLabel,
      bias_state:         biasState,
      bias_reason:        biasReason,
      credibility:        credLabel,
      credibility_state:  credState,
      credibility_reason: credReason,
      scam_risk:          scamLabel,
      scam_reason:        scamReason,
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

