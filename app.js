const inputEl       = document.getElementById("input");
const submitBtn     = document.getElementById("submit");
const statusEl      = document.getElementById("status");
const resultsEl     = document.getElementById("results");
const copyBtn       = document.getElementById("copy");
const pdfBtn        = document.getElementById("pdf-btn");
const audioPlayer   = document.getElementById("audio-player");
const audioBlock    = document.getElementById("audio-block");
const contentText   = document.getElementById("content-text");

const statWords  = document.getElementById("stat-words");
const statSource = document.getElementById("stat-source");
const statType   = document.getElementById("stat-type");
const statMethod = document.getElementById("stat-method");

const biasValue        = document.getElementById("bias-value");
const credibilityValue = document.getElementById("credibility-value");
const scamValue        = document.getElementById("scam-value");
const metricBias       = document.getElementById("metric-bias");
const metricCred       = document.getElementById("metric-credibility");
const metricScam       = document.getElementById("metric-scam");

function setStatus(msg) {
  if (statusEl) statusEl.textContent = msg;
}

/**
 * Update a metric card.
 * state: "good" | "warn" | "bad" | "neutral"
 */
function applyMetric(cardEl, valueEl, label, state) {
  const dot = cardEl?.querySelector(".metric-dot");
  if (dot) dot.dataset.state = state;
  if (cardEl) cardEl.dataset.active = state === "neutral" ? "" : state;
  if (valueEl) valueEl.textContent = label;
}

function showResults(data) {
  // ── Stats ──────────────────────────────────────
  if (statWords)  statWords.textContent  = data.word_count != null ? Number(data.word_count).toLocaleString() : "—";
  if (statSource) statSource.textContent = data.source ?? "—";
  if (statType)   statType.textContent   = data.input_type ?? "—";
  if (statMethod) statMethod.textContent = data.extraction_method ?? "—";

  // ── Metrics (populated when API returns them) ──
  const bias = data.bias ?? null;
  if (bias != null) {
    const s = /none|low/i.test(bias) ? "good" : /moderate|medium/i.test(bias) ? "warn" : "bad";
    applyMetric(metricBias, biasValue, bias, s);
  } else {
    applyMetric(metricBias, biasValue, "—", "neutral");
  }

  const cred = data.credibility ?? null;
  if (cred != null) {
    const s = /high|credible|reliable/i.test(cred) ? "good" : /moderate|mixed/i.test(cred) ? "warn" : "bad";
    applyMetric(metricCred, credibilityValue, cred, s);
  } else {
    applyMetric(metricCred, credibilityValue, "—", "neutral");
  }

  const scam = data.scam_risk ?? data.scam ?? null;
  if (scam != null) {
    const s = /none|low/i.test(scam) ? "good" : /moderate|medium/i.test(scam) ? "warn" : "bad";
    applyMetric(metricScam, scamValue, scam, s);
  } else {
    applyMetric(metricScam, scamValue, "—", "neutral");
  }

  // ── PDF ────────────────────────────────────────
  if (data.pdf_url && pdfBtn) {
    pdfBtn.href = data.pdf_url;
    pdfBtn.removeAttribute("aria-disabled");
  } else if (pdfBtn) {
    pdfBtn.setAttribute("aria-disabled", "true");
    pdfBtn.href = "#";
  }

  // ── Audio ──────────────────────────────────────
  if (data.audio_url && audioPlayer) {
    audioPlayer.src = data.audio_url;
    if (audioBlock) audioBlock.style.display = "";
  } else if (audioBlock) {
    audioBlock.style.display = "none";
  }

  // ── Content ────────────────────────────────────
  if (contentText) {
    contentText.textContent = data.content ?? data.error ?? "No content returned.";
  }

  // ── Show panel ─────────────────────────────────
  if (resultsEl) {
    resultsEl.hidden = false;
    resultsEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}

async function runRequest() {
  const input = inputEl?.value.trim() || "";
  if (!input) {
    setStatus("Enter a URL or some text first.");
    inputEl?.focus();
    return;
  }

  submitBtn.disabled = true;
  setStatus("Analyzing…");
  if (resultsEl) resultsEl.hidden = true;

  try {
    const res = await fetch(`${window.location.origin}/extract`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input }),
    });

    const data = await res.json();
    showResults(data);
    setStatus(res.ok ? "" : `Error ${res.status}`);
  } catch (err) {
    setStatus("Network error — is the API running?");
  } finally {
    submitBtn.disabled = false;
  }
}

submitBtn?.addEventListener("click", runRequest);

inputEl?.addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === "Enter") runRequest();
});

copyBtn?.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(contentText?.textContent ?? "");
    const prev = copyBtn.textContent;
    copyBtn.textContent = "Copied!";
    setTimeout(() => { copyBtn.textContent = prev; }, 1800);
  } catch {
    setStatus("Could not copy.");
  }
});
