/**
 * app.js — CampusBrief frontend logic
 * 3-step AI pipeline UI: Classify → Extract → Plan
 */

// ============================================================
// DOM refs
// ============================================================
const $sampleSelect = document.getElementById("sample-select");
const $inputText = document.getElementById("input-text");
const $charCount = document.getElementById("char-count");
const $generateBtn = document.getElementById("generate-btn");
const $modeBadge = document.getElementById("mode-badge");
const $placeholder = document.getElementById("placeholder");
const $loading = document.getElementById("loading");
const $loadingSub = document.getElementById("loading-sub");
const $result = document.getElementById("result");
const $errorBar = document.getElementById("error-bar");
const $typeBadge = document.getElementById("type-badge");
const $workflowLog = document.getElementById("workflow-log");
const $actionCard = document.getElementById("action-card");
const $naiveSummary = document.getElementById("naive-summary");
const $cardPreview = document.getElementById("card-preview");
const $fieldsGrid = document.getElementById("fields-grid");

const $uploadZone = document.getElementById("upload-zone");
const $fileInput = document.getElementById("file-input");
const $uploadStatus = document.getElementById("upload-status");

const $timeline = document.getElementById("timeline");
const $timelineEmpty = document.getElementById("timeline-empty");

const $historyList = document.getElementById("history-list");
const $btnClearHistory = document.getElementById("btn-clear-history");

const $btnCopy = document.getElementById("btn-copy");
const $btnDownload = document.getElementById("btn-download");
const $btnExportCal = document.getElementById("btn-export-cal");

const $tabs = Array.from(document.querySelectorAll(".tab"));
const $tabContents = Array.from(document.querySelectorAll(".tab-content"));

let currentResult = null;
let cachedSampleText = "";
let currentTimelineItems = [];

// ============================================================
// INIT
// ============================================================
document.addEventListener("DOMContentLoaded", init);

async function init() {
  bindTabs();
  bindKeyboardShortcut();
  bindUpload();
  bindExportButtons();
  bindHistoryClear();
  updateCharCount();

  try {
    const mode = await api("/api/mode");
    $modeBadge.textContent = mode.demo ? "DEMO MODE" : "API MODE";
    $modeBadge.classList.add(mode.demo ? "demo" : "api");
  } catch (e) {
    console.warn("Mode check failed:", e);
    $modeBadge.textContent = "OFFLINE";
  }

  try {
    const names = await api("/api/samples");
    names.forEach((n) => {
      const opt = document.createElement("option");
      opt.value = n;
      opt.textContent = n;
      $sampleSelect.appendChild(opt);
    });
  } catch (e) {
    console.warn("Sample load failed:", e);
  }

  await loadHistory();
  rerenderIcons();
}

// ============================================================
// API
// ============================================================
async function api(url, options = {}) {
  const res = await fetch(url, options);

  let data = null;
  try {
    data = await res.json();
  } catch {
    throw new Error(`Server error (${res.status}). Please try again.`);
  }

  if (!res.ok) {
    throw new Error(data?.error || "Request failed");
  }

  return data;
}

// ============================================================
// UTIL
// ============================================================
function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function rerenderIcons() {
  if (window.lucide && typeof window.lucide.createIcons === "function") {
    window.lucide.createIcons();
  }
}

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

function capitalizeWords(text) {
  return String(text || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

const VALID_TYPES = new Set(["assignment", "competition", "event", "exam", "application", "notice"]);
function safeType(t) {
  return VALID_TYPES.has(t) ? t : "notice";
}

function showError(message) {
  hideLoading();
  $placeholder.hidden = true;
  $result.hidden = false;
  $errorBar.hidden = false;
  $errorBar.innerHTML = `<span>${esc(message)}</span><button class="error-retry" id="error-retry-btn">Retry</button>`;
  document.getElementById("error-retry-btn")?.addEventListener("click", () => {
    clearError();
    generate();
  });
  // Hide stale content from previous successful generation
  $tabContents.forEach((c) => c.classList.remove("active"));
  $tabs.forEach((t) => {
    t.classList.remove("active");
    t.setAttribute("aria-selected", "false");
  });
  $workflowLog.style.display = "none";
  const rh = document.querySelector(".result-header");
  if (rh) rh.style.display = "none";
}

function clearError() {
  $errorBar.hidden = true;
  $errorBar.textContent = "";
}

function flashButton(btn, html, duration = 1200) {
  if (!btn) return;
  const old = btn.innerHTML;
  btn.innerHTML = html;
  btn.disabled = true;
  rerenderIcons();
  setTimeout(() => {
    btn.innerHTML = old;
    btn.disabled = false;
    rerenderIcons();
  }, duration);
}

function downloadTextFile(filename, content, type = "text/plain;charset=utf-8") {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function parseDateFromText(str) {
  if (!str) return null;

  const months = { jan:0, feb:1, mar:2, apr:3, may:4, jun:5, jul:6, aug:7, sep:8, oct:9, nov:10, dec:11,
                   january:0, february:1, march:2, april:3, june:5, july:6, august:7, september:8, october:9, november:10, december:11 };

  // DD Month YYYY — "17 April 2026"
  let m = str.match(/(\d{1,2})\s+(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{4})/i);
  if (m) return new Date(parseInt(m[3]), months[m[2].toLowerCase()], parseInt(m[1]));

  // Month DD, YYYY — "April 17, 2026"
  m = str.match(/(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{1,2}),?\s+(\d{4})/i);
  if (m) return new Date(parseInt(m[3]), months[m[1].toLowerCase()], parseInt(m[2]));

  // ISO: YYYY-MM-DD
  m = str.match(/(\d{4})-(\d{2})-(\d{2})/);
  if (m) return new Date(parseInt(m[1]), parseInt(m[2]) - 1, parseInt(m[3]));

  // DD/MM/YYYY or DD-MM-YYYY
  m = str.match(/(\d{1,2})[-/](\d{1,2})[-/](20\d{2})/);
  if (m) return new Date(parseInt(m[3]), parseInt(m[2]) - 1, parseInt(m[1]));

  // Fallback: DD Month (no year — assume current year)
  m = str.match(/(\d{1,2})\s+(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)/i);
  if (m) return new Date(new Date().getFullYear(), months[m[2].toLowerCase()], parseInt(m[1]));

  // Fallback: Month DD (no year)
  m = str.match(/(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{1,2})/i);
  if (m) return new Date(new Date().getFullYear(), months[m[1].toLowerCase()], parseInt(m[2]));

  return null;
}

function formatShortDate(date) {
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function toIcsDate(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}${m}${d}`;
}

// ============================================================
// LOADING STEP ICON HELPERS
// ============================================================
function getStepEl(stepId) {
  return document.getElementById(stepId);
}

function setStepIcon(stepEl, iconName, spinning = false) {
  if (!stepEl) return;

  let icon = stepEl.querySelector(".step-lucide");
  if (!icon) {
    icon = document.createElement("i");
    icon.className = "step-lucide";
    const dot = stepEl.querySelector(".pstep-dot");
    if (dot) {
      dot.innerHTML = "";
      dot.appendChild(icon);
    }
  }

  icon.setAttribute("data-lucide", iconName);

  if (spinning) {
    icon.classList.add("spin");
  } else {
    icon.classList.remove("spin");
  }
}

function resetStep(stepId) {
  const step = getStepEl(stepId);
  if (!step) return;

  step.classList.remove("active", "done");
  setStepIcon(step, "circle", false);
}

function setStepActive(stepId) {
  const step = getStepEl(stepId);
  if (!step) return;

  step.classList.remove("done");
  step.classList.add("active");
  setStepIcon(step, "loader-circle", true);
}

function setStepDone(stepId) {
  const step = getStepEl(stepId);
  if (!step) return;

  step.classList.remove("active");
  step.classList.add("done");
  setStepIcon(step, "check", false);
}

// ============================================================
// SAMPLE LOADING
// ============================================================
async function loadSample(name) {
  if (!name) {
    $inputText.value = "";
    cachedSampleText = "";
    updateCharCount();
    return;
  }

  try {
    const data = await api(`/api/sample/${encodeURIComponent(name)}`);
    $inputText.value = data.text || "";
    cachedSampleText = ($inputText.value || "").trim();
    updateCharCount();
  } catch (e) {
    console.warn("Load sample failed:", e);
  }
}

$sampleSelect?.addEventListener("change", () => {
  loadSample($sampleSelect.value);
});

// ============================================================
// INPUT / COUNT
// ============================================================
function updateCharCount() {
  const text = $inputText.value || "";
  const chars = text.length;

  const cjk = (text.match(/[\u4e00-\u9fff\u3400-\u4dbf]/g) || []).length;
  const nonCjk = text.replace(/[\u4e00-\u9fff\u3400-\u4dbf]/g, " ").trim();
  const enWords = nonCjk ? nonCjk.split(/\s+/).filter(Boolean).length : 0;
  const words = cjk + enWords;

  $charCount.textContent = `${words.toLocaleString()} words · ${chars.toLocaleString()} chars`;
}

$inputText?.addEventListener("input", updateCharCount);

// ============================================================
// KEYBOARD
// ============================================================
function bindKeyboardShortcut() {
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && !$generateBtn.disabled) {
      generate();
    }
  });
}

// ============================================================
// GENERATE
// ============================================================
$generateBtn?.addEventListener("click", generate);

async function generate() {
  const text = ($inputText.value || "").trim();

  if (!text) {
    showError("Please paste a campus brief or select a sample to get started.");
    return;
  }

  clearError();
  showLoading();

  let sampleName = "";
  if ($sampleSelect.value && cachedSampleText && text === cachedSampleText) {
    sampleName = $sampleSelect.value;
  }

  $generateBtn.disabled = true;
  $generateBtn.innerHTML = `
    <i data-lucide="loader-circle" class="btn-icon spin"></i>
    <span>Generating...</span>
  `;
  rerenderIcons();

  try {
    const t0 = Date.now();

    // Hard timeout: abort if API takes longer than 60s
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60000);

    const result = await api("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, sample_name: sampleName }),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    // Ensure loading animation plays for at least 3.5s so the
    // Classify → Extract → Plan steps are visible to the user
    const elapsed = Date.now() - t0;
    const minDisplay = 3500;
    if (elapsed < minDisplay) {
      await new Promise((r) => setTimeout(r, minDisplay - elapsed));
    }

    currentResult = result;
    renderResult(result);
    await loadHistory();

    $result.closest(".panel-output")?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  } catch (e) {
    const msg = e.name === "AbortError"
      ? "Request timed out after 60 seconds. Please try again or switch to Demo mode."
      : (e.message || "Generation failed");
    showError(msg);
  } finally {
    $generateBtn.disabled = false;
    $generateBtn.innerHTML = `
      <i data-lucide="sparkles" class="btn-icon"></i>
      <span>Generate Action Card</span>
    `;
    rerenderIcons();
  }
}

// ============================================================
// LOADING
// ============================================================
function showLoading() {
  $placeholder.hidden = true;
  $result.hidden = true;
  $loading.hidden = false;
  clearError();

  document.querySelectorAll(".pstep-line").forEach((el) => el.classList.remove("done"));

  resetStep("step-classify");
  resetStep("step-extract");
  resetStep("step-plan");

  setStepActive("step-classify");
  $loadingSub.textContent = "Step 1/3 — Identifying document type...";
  rerenderIcons();

  const transitions = [
    {
      done: "step-classify",
      next: "step-extract",
      lineIdx: 0,
      text: "Step 2/3 — Extracting structured fields...",
      delay: 1200,
    },
    {
      done: "step-extract",
      next: "step-plan",
      lineIdx: 1,
      text: "Step 3/3 — Generating action plan...",
      delay: 2600,
    },
    {
      done: "step-plan",
      next: null,
      lineIdx: null,
      text: "Finalizing...",
      delay: 4000,
    },
  ];

  const lines = document.querySelectorAll(".pstep-line");

  transitions.forEach((t) => {
    setTimeout(() => {
      if ($loading.hidden) return;

      setStepDone(t.done);

      if (t.lineIdx !== null && lines[t.lineIdx]) {
        lines[t.lineIdx].classList.add("done");
      }

      if (t.next) {
        setStepActive(t.next);
      }

      $loadingSub.textContent = t.text;
      rerenderIcons();
    }, t.delay);
  });

  setTimeout(() => {
    if (!$loading.hidden) {
      $loadingSub.textContent = "Still processing — AI is generating your action card...";
    }
  }, 8000);

  setTimeout(() => {
    if (!$loading.hidden) {
      $loadingSub.textContent = "Almost there — assembling final results...";
    }
  }, 18000);
}

function hideLoading() {
  $loading.hidden = true;
}

// ============================================================
// RENDER RESULT
// ============================================================
function renderResult(r) {
  hideLoading();
  $result.hidden = false;
  $placeholder.hidden = true;

  if (r.error) {
    showError(r.error);
    return;
  }

  clearError();

  // Restore elements that showError may have hidden
  const rh = document.querySelector(".result-header");
  if (rh) rh.style.display = "";

  const taskType = safeType(r.task_type);
  const typeDisplay = capitalizeWords(taskType);
  $typeBadge.textContent = typeDisplay;
  $typeBadge.className = `type-badge tb-${taskType}`;

  const existingConf = document.getElementById("conf-badge");
  if (existingConf) existingConf.remove();

  const safeConf = ["high", "medium", "low"].includes(r.confidence) ? r.confidence : "medium";
  if (r.confidence) {
    const confEl = document.createElement("span");
    confEl.id = "conf-badge";
    confEl.className = `conf-badge conf-${safeConf}`;
    confEl.textContent = String(r.confidence).toUpperCase();
    $typeBadge.parentElement?.appendChild(confEl);
  }

  renderWorkflowLog(r.workflow_log || []);
  renderActionCard(r.action_card || {});
  renderCardPreview(r.action_card || {});
  renderFields(r.structured_data || {});
  renderTimeline(r.structured_data || {}, r.action_card || {});
  $naiveSummary.textContent = r.naive_summary || "No summary available.";

  switchTab("tab-action");
  rerenderIcons();
}

function renderWorkflowLog(logs) {
  const wl = safeArray(logs);
  if (!wl.length) {
    $workflowLog.innerHTML = "";
    $workflowLog.style.display = "none";
    return;
  }

  $workflowLog.style.display = "";
  const isApiMode = wl.some((e) => typeof e === "string" && e.includes("LLM calls"));
  const callLabel = isApiMode
    ? '<span class="wl-call-count">4 LLM calls</span>'
    : '<span class="wl-demo-tag">Demo</span>';

  $workflowLog.innerHTML =
    `<div class="wl-header">
      <span class="wl-title">Pipeline Trace</span>
      ${callLabel}
    </div>` +
    wl.map((entry, i) => {
      return `
        <div class="wl-row">
          <span class="wl-step-num">${i + 1}</span>
          <span>${entry}</span>
        </div>
      `;
    }).join("");
}

// ============================================================
// ACTION CARD
// ============================================================
function renderActionCard(card) {
  const bullets = (arr, prefix = "") => {
    const items = safeArray(arr);
    if (!items.length) return "<p><em>None</em></p>";
    return `<ul>${items.map((x) => `<li>${prefix}${esc(x)}</li>`).join("")}</ul>`;
  };

  const team = card.team_actions || {};

  $actionCard.innerHTML = `
    <div class="ac-header">
      <i data-lucide="clipboard-check" class="module-icon"></i>
      <span>Action Card</span>
    </div>

    <div class="module mod-info">
      <h4><i data-lucide="flag" class="module-icon"></i><span>What is this task?</span></h4>
      <p>${esc(card.what_is_this_task || "N/A")}</p>
    </div>

    <div class="module">
      <h4><i data-lucide="list-checks" class="module-icon"></i><span>Key Requirements</span></h4>
      ${bullets(card.key_requirements)}
    </div>

    <div class="module mod-success">
      <h4><i data-lucide="package-check" class="module-icon"></i><span>Deliverables & Deadlines</span></h4>
      ${bullets(card.deliverables_and_deadlines)}
    </div>

    <div class="module">
      <h4><i data-lucide="users" class="module-icon"></i><span>Team Actions</span></h4>
      <div class="step-row"><span class="step-badge step-first">First</span><span class="step-text">${esc(team.first || "N/A")}</span></div>
      <div class="step-row"><span class="step-badge step-next">Next</span><span class="step-text">${esc(team.next || "N/A")}</span></div>
      <div class="step-row"><span class="step-badge step-final">Final</span><span class="step-text">${esc(team.final || "N/A")}</span></div>
    </div>

    <div class="module mod-warning">
      <h4><i data-lucide="triangle-alert" class="module-icon"></i><span>Risks / Missing Info</span></h4>
      ${bullets(card.risks_and_missing_info, "⚠ ")}
    </div>
  `;
}

// ============================================================
// CARD PREVIEW / COMPARE
// ============================================================
function renderCardPreview(card) {
  const team = card.team_actions || {};
  const deadlines = safeArray(card.deliverables_and_deadlines);
  const risks = safeArray(card.risks_and_missing_info);
  const reqs = safeArray(card.key_requirements);

  const miniList = (arr, max = 2) => {
    if (!arr.length) return "<p class='cp-more'>None</p>";
    const shown = arr.slice(0, max);
    const more = arr.length > max ? `<li class="cp-more">+ ${arr.length - max} more</li>` : "";
    return `<ul class="cp-list">${shown.map((x) => `<li>${esc(x)}</li>`).join("")}${more}</ul>`;
  };

  $cardPreview.innerHTML = `
    <div class="cp-section"><strong>Task:</strong> ${esc(card.what_is_this_task || "N/A")}</div>
    <div class="cp-section"><strong>Key Requirements</strong> (${reqs.length})${miniList(reqs)}</div>
    <div class="cp-section"><strong>Deadlines</strong> (${deadlines.length})${miniList(deadlines)}</div>
    <div class="cp-section">
      <strong>Team Actions:</strong>
      <span class="cp-step">First</span> → <span class="cp-step">Next</span> → <span class="cp-step">Final</span>
      <div class="cp-list">
        <div>${esc(team.first || "N/A")}</div>
        <div>${esc(team.next || "N/A")}</div>
        <div>${esc(team.final || "N/A")}</div>
      </div>
    </div>
    <div class="cp-section"><strong>Risks</strong> (${risks.length})${miniList(risks, 1)}</div>
  `;
}

// ============================================================
// FIELDS
// ============================================================
function renderFields(sd) {
  const fieldList = (arr, cls = "") => {
    const list = safeArray(arr);
    if (!list.length) return "<p>None</p>";
    return `<ul>${list.map((x) => `<li class="${cls}">${cls === "warn" ? "⚠ " : ""}${esc(x)}</li>`).join("")}</ul>`;
  };

  $fieldsGrid.innerHTML = `
    <div class="field-group">
      <h4>Objective</h4>
      <blockquote>${esc(sd.objective || "Not specified")}</blockquote>
    </div>

    <div class="field-group">
      <h4>Key Requirements</h4>
      ${fieldList(sd.key_requirements)}
    </div>

    <div class="field-group">
      <h4>Deliverables</h4>
      ${fieldList(sd.deliverables)}
    </div>

    <div class="field-group">
      <h4>Deadlines</h4>
      ${fieldList(sd.deadlines)}
    </div>

    <div class="field-group">
      <h4>Constraints</h4>
      ${fieldList(sd.constraints)}
    </div>

    <div class="field-group">
      <h4>Important Notes</h4>
      ${fieldList(sd.important_notes)}
    </div>

    <div class="field-group">
      <h4>Missing Info</h4>
      ${fieldList(sd.missing_info, "warn")}
    </div>
  `;
}

// ============================================================
// TIMELINE
// ============================================================
function renderTimeline(sd, card) {
  const deadlines = safeArray(card.deliverables_and_deadlines).length
    ? safeArray(card.deliverables_and_deadlines)
    : safeArray(sd.deadlines);
  currentTimelineItems = [];

  deadlines.forEach((item) => {
    const text = String(item || "").trim();
    if (!text) return;

    const date = parseDateFromText(text);
    if (!date) return;

    currentTimelineItems.push({ date, full: text });
  });

  if (!currentTimelineItems.length) {
    $timeline.innerHTML = "";
    $timeline.hidden = true;
    $timelineEmpty.hidden = false;
    if ($btnExportCal) $btnExportCal.hidden = true;
    return;
  }

  $timeline.hidden = false;
  $timelineEmpty.hidden = true;
  if ($btnExportCal) $btnExportCal.hidden = false;

  currentTimelineItems.sort((a, b) => a.date - b.date);

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  // Build vertical timeline items
  const rows = currentTimelineItems.map((item) => {
    const daysDiff = Math.ceil((item.date - today) / (1000 * 60 * 60 * 24));

    let statusClass = "";
    let statusLabel = "";
    if (daysDiff < 0) {
      statusClass = "tl-past";
      statusLabel = `${Math.abs(daysDiff)}d ago`;
    } else if (daysDiff === 0) {
      statusClass = "tl-today";
      statusLabel = "Today";
    } else if (daysDiff <= 3) {
      statusClass = "tl-urgent";
      statusLabel = `${daysDiff}d left`;
    } else if (daysDiff <= 7) {
      statusClass = "tl-soon";
      statusLabel = `${daysDiff}d left`;
    } else {
      statusClass = "tl-future";
      statusLabel = `${daysDiff}d left`;
    }

    return `
      <div class="tl-item ${statusClass}">
        <div class="tl-dot-col">
          <div class="tl-dot"></div>
        </div>
        <div class="tl-content">
          <div class="tl-date-row">
            <span class="tl-date">${esc(formatShortDate(item.date))}</span>
            <span class="tl-status">${statusLabel}</span>
          </div>
          <div class="tl-text">${esc(item.full)}</div>
        </div>
      </div>
    `;
  }).join("");

  $timeline.innerHTML = `<div class="tl-vertical">${rows}</div>`;
}

// ============================================================
// TABS
// ============================================================
function bindTabs() {
  $tabs.forEach((btn) => {
    btn.addEventListener("click", () => {
      switchTab(btn.dataset.tab);
    });
  });

  const teaserLink = document.getElementById("teaser-link");
  teaserLink?.addEventListener("click", (e) => {
    e.preventDefault();
    switchTab("tab-compare");
  });
}

function switchTab(tabId) {
  $tabs.forEach((btn) => {
    const isActive = btn.dataset.tab === tabId;
    btn.classList.toggle("active", isActive);
    btn.setAttribute("aria-selected", isActive ? "true" : "false");
  });

  $tabContents.forEach((panel) => {
    panel.classList.toggle("active", panel.id === tabId);
  });
}

// ============================================================
// COPY / DOWNLOAD / ICS
// ============================================================
function bindExportButtons() {
  $btnCopy?.addEventListener("click", async () => {
    if (!currentResult) return;

    const md = buildMarkdown(currentResult);
    try {
      await navigator.clipboard.writeText(md);
      flashButton(
        $btnCopy,
        `<i data-lucide="check" class="btn-sm-icon"></i><span>Copied!</span>`
      );
    } catch {
      downloadTextFile("campusbrief-action-card.md", md, "text/markdown;charset=utf-8");
    }
  });

  $btnDownload?.addEventListener("click", () => {
    if (!currentResult) return;
    const md = buildMarkdown(currentResult);
    downloadTextFile("campusbrief-action-card.md", md, "text/markdown;charset=utf-8");
  });

  $btnExportCal?.addEventListener("click", () => {
    if (!currentTimelineItems.length) return;

    const now = new Date();
    const dtstamp =
      now.getUTCFullYear().toString() +
      String(now.getUTCMonth() + 1).padStart(2, "0") +
      String(now.getUTCDate()).padStart(2, "0") + "T" +
      String(now.getUTCHours()).padStart(2, "0") +
      String(now.getUTCMinutes()).padStart(2, "0") +
      String(now.getUTCSeconds()).padStart(2, "0") + "Z";

    let ics = "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//CampusBrief//EN\r\nCALSCALE:GREGORIAN\r\n";

    currentTimelineItems.forEach((item) => {
      const dateStr = toIcsDate(item.date);

      const nextDay = new Date(item.date);
      nextDay.setDate(nextDay.getDate() + 1);
      const endStr = toIcsDate(nextDay);

      const summary = item.full.replace(/[\r\n]+/g, " ").replace(/[\\;,]/g, (c) => "\\" + c);
      const uid = `${dateStr}-${Math.random().toString(36).slice(2, 8)}@campusbrief`;

      ics += "BEGIN:VEVENT\r\n";
      ics += `DTSTART;VALUE=DATE:${dateStr}\r\n`;
      ics += `DTEND;VALUE=DATE:${endStr}\r\n`;
      ics += `SUMMARY:${summary}\r\n`;
      ics += `DTSTAMP:${dtstamp}\r\n`;
      ics += `UID:${uid}\r\n`;
      ics += "END:VEVENT\r\n";
    });

    ics += "END:VCALENDAR\r\n";

    const blob = new Blob([ics], { type: "text/calendar;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `deadlines-${Date.now()}.ics`;
    a.click();
    URL.revokeObjectURL(url);

    flashButton(
      $btnExportCal,
      `<i data-lucide="check" class="btn-sm-icon"></i><span>Exported!</span>`,
      1500
    );
  });
}

function buildMarkdown(result) {
  const card = result?.action_card || {};
  const team = card.team_actions || {};
  const sd = result?.structured_data || {};

  const toBullets = (arr) => {
    const items = safeArray(arr);
    return items.length ? items.map((x) => `- ${x}`).join("\n") : "- None";
  };

  return `# CampusBrief Action Card

## Task Type
${capitalizeWords(result?.task_type || "notice")}

## What is this task?
${card.what_is_this_task || "N/A"}

## Key Requirements
${toBullets(card.key_requirements)}

## Deliverables & Deadlines
${toBullets(card.deliverables_and_deadlines)}

## Team Actions
- First: ${team.first || "N/A"}
- Next: ${team.next || "N/A"}
- Final: ${team.final || "N/A"}

## Risks / Missing Info
${toBullets(card.risks_and_missing_info)}

## Extracted Deadlines
${toBullets(sd.deadlines)}
`;
}

// ============================================================
// UPLOAD
// ============================================================
function bindUpload() {
  if (!$uploadZone || !$fileInput) return;

  const uploadLink = document.getElementById("upload-link");

  uploadLink?.addEventListener("click", (e) => {
    e.preventDefault();
    $fileInput.click();
  });

  $uploadZone.addEventListener("click", (e) => {
    if (e.target?.id === "upload-link") return;
    $fileInput.click();
  });

  $uploadZone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      $fileInput.click();
    }
  });

  ["dragenter", "dragover"].forEach((evt) => {
    $uploadZone.addEventListener(evt, (e) => {
      e.preventDefault();
      e.stopPropagation();
      $uploadZone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach((evt) => {
    $uploadZone.addEventListener(evt, (e) => {
      e.preventDefault();
      e.stopPropagation();
      $uploadZone.classList.remove("dragover");
    });
  });

  $uploadZone.addEventListener("drop", async (e) => {
    const file = e.dataTransfer?.files?.[0];
    if (file) {
      await uploadFile(file);
    }
  });

  $fileInput.addEventListener("change", async () => {
    const file = $fileInput.files?.[0];
    if (file) {
      await uploadFile(file);
    }
  });
}

async function uploadFile(file) {
  const allowed = [".pdf", ".docx", ".txt"];
  const lower = file.name.toLowerCase();

  if (!allowed.some((ext) => lower.endsWith(ext))) {
    showUploadStatus("Only PDF, DOCX, and TXT files are supported.", true);
    return;
  }

  if (file.size > 10 * 1024 * 1024) {
    showUploadStatus("File is too large. Please upload a file under 10MB.", true);
    return;
  }

  showUploadStatus(`Uploading ${file.name}...`, false);

  const formData = new FormData();
  formData.append("file", file);

  try {
    const data = await api("/api/upload", {
      method: "POST",
      body: formData,
    });

    $inputText.value = data.text || "";
    cachedSampleText = "";
    $sampleSelect.value = "";
    updateCharCount();

    showUploadStatus(`Loaded ${file.name} successfully.`, false);
    setTimeout(() => { if ($uploadStatus) $uploadStatus.hidden = true; }, 4000);
  } catch (e) {
    showUploadStatus(e.message || "Upload failed.", true);
  } finally {
    $fileInput.value = "";
  }
}

function showUploadStatus(message, isError = false) {
  if (!$uploadStatus) return;
  $uploadStatus.hidden = false;
  $uploadStatus.textContent = message;
  $uploadStatus.classList.remove("success", "error");
  $uploadStatus.classList.add(isError ? "error" : "success");
}

// ============================================================
// HISTORY
// ============================================================
let _historyDelegated = false;

async function loadHistory() {
  if (!$historyList) return;

  // Attach event delegation once — avoids duplicate listeners on re-render
  if (!_historyDelegated) {
    _historyDelegated = true;
    $historyList.addEventListener("click", async (e) => {
      const deleteBtn = e.target.closest(".hc-delete");
      if (deleteBtn) {
        e.stopPropagation();
        const id = deleteBtn.dataset.id;
        try {
          await api(`/api/history/${encodeURIComponent(id)}`, { method: "DELETE" });
          await loadHistory();
        } catch (err) {
          console.warn("Delete history failed:", err);
        }
        return;
      }

      const card = e.target.closest(".history-card");
      if (card) {
        const id = card.dataset.id;
        try {
          const rec = await api(`/api/history/${encodeURIComponent(id)}`);
          if (rec.result) {
            currentResult = rec.result;
            renderResult(rec.result);
          }
          $result.closest(".panel-output")?.scrollIntoView({
            behavior: "smooth",
            block: "start",
          });
        } catch (err) {
          showError(err.message || "Failed to load history item.");
        }
      }
    });
  }

  try {
    const rows = await api("/api/history");
    const list = safeArray(rows);

    if (!list.length) {
      $historyList.innerHTML = `<p class="history-empty">No history yet. Generate an action card to get started.</p>`;
      return;
    }

    $historyList.innerHTML = list.map((item) => {
      return `
        <div class="history-card" data-id="${item.id}">
          <button class="hc-delete" data-id="${item.id}" title="Delete">&times;</button>
          <span class="hc-type type-${safeType(item.task_type)}">${esc(capitalizeWords(item.task_type || "notice"))}</span>
          <div class="hc-preview">${esc(item.input_preview || "")}</div>
          <div class="hc-time">${esc(item.created_at || "")}</div>
        </div>
      `;
    }).join("");
  } catch (e) {
    console.warn("History load failed:", e);
    $historyList.innerHTML = `<p class="history-empty">Failed to load history.</p>`;
  }
}

function bindHistoryClear() {
  $btnClearHistory?.addEventListener("click", async () => {
    if (!confirm("Clear all history?")) return;
    try {
      await api("/api/history", { method: "DELETE" });
      await loadHistory();
      flashButton(
        $btnClearHistory,
        `<i data-lucide="check" class="btn-sm-icon"></i><span>Cleared</span>`
      );
    } catch (e) {
      console.warn("Clear history failed:", e);
    }
  });
}