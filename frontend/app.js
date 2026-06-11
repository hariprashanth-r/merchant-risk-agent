// Talks to the FastAPI backend and renders results.
// No framework on purpose: for a first full-stack project, plain fetch + DOM
// keeps the moving parts visible. Swap in React once the contract is clear.

const $ = (id) => document.getElementById(id);

const runBtn = $("runBtn");
const statusEl = $("status");
const resultEl = $("result");

runBtn.addEventListener("click", investigate);
document.addEventListener("DOMContentLoaded", loadHistory);

async function investigate() {
  const merchant_name = $("merchantName").value.trim();
  const website = $("website").value.trim();

  if (!merchant_name || !website) {
    setStatus("Enter both a merchant name and a website.", "error");
    return;
  }

  runBtn.disabled = true;
  setStatus("Investigating… the agent is fetching the site, screening sanctions, and checking the domain.");
  resultEl.hidden = true;

  try {
    const res = await fetch("/api/investigate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ merchant_name, website }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Server returned ${res.status}`);
    }

    const report = await res.json();
    renderReport(report);
    setStatus("Done.");
    loadHistory();
  } catch (e) {
    setStatus(`Investigation failed: ${e.message}`, "error");
  } finally {
    runBtn.disabled = false;
  }
}

function renderReport(r) {
  const stamp = $("stamp");
  stamp.textContent = r.recommendation;
  stamp.dataset.verdict = r.recommendation;

  $("scoreValue").textContent = r.risk_score;
  // delay so the CSS width transition is visible
  requestAnimationFrame(() => {
    $("scoreFill").style.width = `${Math.max(0, Math.min(100, r.risk_score))}%`;
  });

  $("summary").textContent = r.summary || "";

  const flags = $("flags");
  flags.innerHTML = "";
  if (!r.flags || r.flags.length === 0) {
    flags.innerHTML = `<li class="flag" data-sev="low"><div class="flag__head"><span class="flag__cat">no_flags</span></div><p class="flag__evidence">No risk signals recorded.</p></li>`;
  } else {
    for (const f of r.flags) {
      const li = document.createElement("li");
      li.className = "flag";
      li.dataset.sev = f.severity;
      li.innerHTML = `
        <div class="flag__head">
          <span class="flag__cat">${escapeHtml(f.category)}</span>
          <span class="chip" data-sev="${f.severity}">${f.severity}</span>
        </div>
        <p class="flag__evidence">${escapeHtml(f.evidence)}</p>`;
      flags.appendChild(li);
    }
  }

  resultEl.hidden = false;
}

async function loadHistory() {
  try {
    const res = await fetch("/api/investigations");
    const rows = await res.json();
    const list = $("caselist");
    if (!rows.length) {
      list.innerHTML = `<li class="caselist__empty">No cases yet.</li>`;
      return;
    }
    list.innerHTML = "";
    for (const row of rows) {
      const li = document.createElement("li");
      li.className = "case";
      li.innerHTML = `
        <span class="case__name" title="${escapeHtml(row.merchant_name)}">${escapeHtml(row.merchant_name)}</span>
        <span style="display:flex;align-items:center;gap:8px;">
          <span style="font-family:'IBM Plex Mono',monospace;">${row.risk_score ?? "—"}</span>
          <span class="case__dot" data-verdict="${row.recommendation}"></span>
        </span>`;
      list.appendChild(li);
    }
  } catch {
    /* history is non-critical; ignore */
  }
}

function setStatus(msg, tone) {
  statusEl.textContent = msg;
  if (tone) statusEl.dataset.tone = tone;
  else delete statusEl.dataset.tone;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}
