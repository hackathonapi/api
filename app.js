const apiBaseEl = document.getElementById("apiBase");
const inputEl = document.getElementById("input");
const submitBtn = document.getElementById("submit");
const statusEl = document.getElementById("status");
const outputEl = document.getElementById("output");
const copyBtn = document.getElementById("copy");

const STORAGE_KEY = "clearways_api_base_url";

function setStatus(text) {
  if (statusEl) statusEl.textContent = text;
}

function setOutput(value) {
  if (outputEl) outputEl.textContent = JSON.stringify(value, null, 2);
}

function normalizedBaseUrl(raw) {
  const trimmed = raw.trim();
  if (!trimmed) return window.location.origin;
  return trimmed.replace(/\/+$/, "");
}

if (apiBaseEl) {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored) apiBaseEl.value = stored;
}

async function runRequest() {
  const input = inputEl?.value.trim() || "";
  if (!input) {
    setStatus("Input is required.");
    inputEl?.focus();
    return;
  }

  submitBtn.disabled = true;
  setStatus("Running...");

  const apiBase = normalizedBaseUrl(apiBaseEl?.value || "");
  localStorage.setItem(STORAGE_KEY, apiBase);
  const url = `${apiBase}/extract`;

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input }),
    });

    const data = await response.json();
    setOutput(data);
    setStatus(response.ok ? "Success." : `Request failed (${response.status}).`);
  } catch (error) {
    setOutput({ error: error instanceof Error ? error.message : "Unknown error" });
    setStatus("Network/CORS error.");
  } finally {
    submitBtn.disabled = false;
  }
}

submitBtn?.addEventListener("click", runRequest);

inputEl?.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") runRequest();
});

copyBtn?.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(outputEl?.textContent || "");
    setStatus("JSON copied.");
  } catch {
    setStatus("Could not copy JSON.");
  }
});
