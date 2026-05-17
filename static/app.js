// ── Auth ──
const token = localStorage.getItem("token");
const user = JSON.parse(localStorage.getItem("user") || "null");

function authHeaders() {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ── DOM refs ──
const form = document.getElementById("evaluateForm");
const urlInput = document.getElementById("urlInput");
const detailInput = document.getElementById("detailInput");
const purposeInput = document.getElementById("purposeInput");
const minPriceInput = document.getElementById("minPriceInput");
const maxPriceInput = document.getElementById("maxPriceInput");
const maxItemsInput = document.getElementById("maxItemsInput");
const useModelInput = document.getElementById("useModelInput");
const submitBtn = document.getElementById("submitBtn");
const sampleBtn = document.getElementById("sampleBtn");
const eventsEl = document.getElementById("events");
const reportEl = document.getElementById("report");
const statusBadge = document.getElementById("statusBadge");
const userDisplay = document.getElementById("userDisplay");
const rulesBtn = document.getElementById("rulesBtn");
const rulesPanel = document.getElementById("rulesPanel");
const rulesEditor = document.getElementById("rulesEditor");
const saveRulesBtn = document.getElementById("saveRulesBtn");
const rulesSaved = document.getElementById("rulesSaved");
const logoutBtn = document.getElementById("logoutBtn");
let streamedReportMarkdown = "";
let currentBatchHadDelta = false;
let renderTimer = null;
let currentRules = {};
let currentRuleTab = "skin_quality";

// ── User bar ──
if (user) userDisplay.textContent = user.username;
logoutBtn.addEventListener("click", () => {
  localStorage.removeItem("token");
  localStorage.removeItem("user");
  window.location.replace("/static/login.html");
});

// ── Rules panel ──
rulesBtn.addEventListener("click", () => {
  rulesPanel.classList.toggle("hidden");
  if (!rulesPanel.classList.contains("hidden")) loadRules();
});

document.querySelectorAll(".rules-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".rules-tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    currentRuleTab = tab.dataset.rule;
    rulesEditor.value = currentRules[currentRuleTab] || "";
  });
});

saveRulesBtn.addEventListener("click", async () => {
  currentRules[currentRuleTab] = rulesEditor.value;
  const resp = await fetch(`/api/rules/${currentRuleTab}`, {
    method: "PUT",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify({ content: rulesEditor.value, title: currentRuleTab }),
  });
  if (resp.ok) {
    rulesSaved.textContent = "已保存";
    setTimeout(() => (rulesSaved.textContent = ""), 2000);
  } else {
    rulesSaved.textContent = "保存失败";
  }
});

async function loadRules() {
  try {
    const resp = await fetch("/api/rules", { headers: authHeaders() });
    if (!resp.ok) throw new Error("获取规则失败");
    const data = await resp.json();
    currentRules = { skin_quality: data.skin_quality || "", system_prompt: data.system_prompt || "", baseline: data.baseline || "" };
    rulesEditor.value = currentRules[currentRuleTab] || "";
  } catch (e) {
    rulesSaved.textContent = "加载规则失败: " + e.message;
  }
}

sampleBtn.addEventListener("click", () => {
  detailInput.value = "售价1300元，3典藏，3无双，2珍品传说，30传说，400左右皮肤，英雄118，可二次实名，平台包赔。";
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  await evaluate();
});

async function evaluate() {
  eventsEl.innerHTML = "";
  streamedReportMarkdown = "";
  currentBatchHadDelta = false;
  renderTimer = null;
  reportEl.textContent = "正在评估...";
  reportEl.classList.add("empty");
  statusBadge.textContent = "运行中";
  submitBtn.disabled = true;

  const payload = {
    session_id: `web-${Date.now()}`,
    url: urlInput.value.trim() || null,
    detail_text: detailInput.value.trim() || null,
    purpose: purposeInput.value.trim() || "共号/出租变现",
    min_price: numberOrNull(minPriceInput.value),
    max_price: numberOrNull(maxPriceInput.value),
    max_items: Number(maxItemsInput.value || 60),
    use_model: useModelInput.checked,
    custom_rules: Object.keys(currentRules).length > 0 ? currentRules : null,
  };

  try {
    const response = await fetch("/api/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok || !response.body) {
      throw new Error(`请求失败：${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const chunks = buffer.split(/\n\n|\r\n\r\n/);
      buffer = chunks.pop() || "";
      for (const chunk of chunks) {
        if (chunk.trim()) parseSseChunk(chunk);
      }
    }
    if (buffer.trim()) parseSseChunk(buffer);
  } catch (error) {
    addEvent({ type: "error", stage: "error", message: error.message });
    statusBadge.textContent = "失败";
  } finally {
    submitBtn.disabled = false;
  }
}

function scheduleRender() {
  if (renderTimer !== null) return;
  renderTimer = setTimeout(() => {
    renderTimer = null;
    renderMarkdown(streamedReportMarkdown);
  }, 100);
}

function flushRender() {
  if (renderTimer !== null) {
    clearTimeout(renderTimer);
    renderTimer = null;
  }
  renderMarkdown(streamedReportMarkdown);
}

function numberOrNull(value) {
  if (value === null || value === undefined || String(value).trim() === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function parseSseChunk(chunk) {
  const normalized = chunk.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  const dataLines = normalized
    .split("\n")
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trim());

  for (const line of dataLines) {
    if (!line || line === "[DONE]") continue;
    const event = JSON.parse(line);
    if (event.type !== "llm_delta") addEvent(event);
    if ((event.type === "report" || event.type === "report_preview") && event.report) {
      renderMarkdown(event.report);
      if (event.type === "report_preview") statusBadge.textContent = "规则报告已出";
    }
    if (event.type === "llm_batches_planned") {
      statusBadge.textContent = `模型复核 0/${event.total_batches || "?"}`;
      streamedReportMarkdown = "# 模型复核流式输出\n\n";
      renderMarkdown(streamedReportMarkdown);
    }
    if (event.type === "llm_batch_start") {
      statusBadge.textContent = `模型复核 ${event.batch || "?"}/${event.total_batches || "?"}`;
      currentBatchHadDelta = false;
      if (!streamedReportMarkdown) streamedReportMarkdown = "# 模型复核流式输出\n\n";
      streamedReportMarkdown += `\n\n## 第 ${event.batch || "?"}/${event.total_batches || "?"} 批\n\n`;
      renderMarkdown(streamedReportMarkdown);
    }
    if (event.type === "llm_delta") {
      currentBatchHadDelta = true;
      if (!streamedReportMarkdown) streamedReportMarkdown = "# 模型复核流式输出\n\n";
      streamedReportMarkdown += event.delta || "";
      scheduleRender();
    }
    if (event.type === "llm_batch_complete") {
      statusBadge.textContent = `模型复核 ${event.batch || "?"}/${event.total_batches || "?"} 完成`;
      if (event.report && !currentBatchHadDelta) {
        if (!streamedReportMarkdown) streamedReportMarkdown = "# 模型复核流式输出\n\n";
        streamedReportMarkdown += `\n\n${event.report}`;
      }
      flushRender();
    }
    if (event.type === "complete") {
      flushRender();
      statusBadge.textContent = "完成";
      if (event.response) renderMarkdown(event.response);
    }
    if (event.type === "error") statusBadge.textContent = "失败";
  }
}

function addEvent(event) {
  const div = document.createElement("div");
  div.className = `event ${event.type || ""}`;

  const title = document.createElement("strong");
  title.textContent = `${event.stage || "status"} · ${event.type || "event"}`;
  div.appendChild(title);

  const message = document.createElement("div");
  message.textContent = event.message || "";
  div.appendChild(message);

  if (event.current_step) {
    const step = document.createElement("div");
    step.textContent = `当前步骤：${event.current_step}`;
    div.appendChild(step);
  }

  if (event.total_batches) {
    const progress = document.createElement("div");
    progress.className = "progress-line";
    const batch = Number(event.batch || 0);
    const total = Number(event.total_batches || 0);
    const percent = total > 0 ? Math.min(100, Math.round((batch / total) * 100)) : 0;
    progress.innerHTML = `<span>模型复核进度</span><div class="progress-track"><i style="width:${percent}%"></i></div><em>${batch || 0}/${total || "?"}</em>`;
    div.appendChild(progress);
  }

  if (Array.isArray(event.plan) && event.plan.length) {
    const ul = document.createElement("ul");
    event.plan.forEach((item) => {
      const li = document.createElement("li");
      li.textContent = item;
      ul.appendChild(li);
    });
    div.appendChild(ul);
  }

  if (Array.isArray(event.warnings) && event.warnings.length) {
    div.classList.add("warning");
    const ul = document.createElement("ul");
    event.warnings.forEach((item) => {
      const li = document.createElement("li");
      li.textContent = item;
      ul.appendChild(li);
    });
    div.appendChild(ul);
  }

  eventsEl.appendChild(div);
  eventsEl.scrollTop = eventsEl.scrollHeight;
}

function renderMarkdown(markdown) {
  reportEl.classList.remove("empty");
  reportEl.innerHTML = markdownToHtml(markdown);
}

function markdownToHtml(markdown) {
  const lines = String(markdown || "").split(/\r?\n/);
  const html = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    const trimmed = line.trim();

    if (!trimmed) {
      index += 1;
      continue;
    }

    const heading = /^(#{1,4})\s+(.+)$/.exec(trimmed);
    if (heading) {
      const level = heading[1].length;
      html.push(`<h${level}>${renderInline(heading[2])}</h${level}>`);
      index += 1;
      continue;
    }

    if (isTableStart(lines, index)) {
      const tableLines = [];
      while (index < lines.length && isTableLine(lines[index])) {
        tableLines.push(lines[index]);
        index += 1;
      }
      html.push(renderTable(tableLines));
      continue;
    }

    if (/^-\s+/.test(trimmed)) {
      const items = [];
      while (index < lines.length && /^-\s+/.test(lines[index].trim())) {
        items.push(`<li>${renderInline(lines[index].trim().replace(/^-\s+/, ""))}</li>`);
        index += 1;
      }
      html.push(`<ul>${items.join("")}</ul>`);
      continue;
    }

    const paragraph = [];
    while (
      index < lines.length &&
      lines[index].trim() &&
      !/^(#{1,4})\s+/.test(lines[index].trim()) &&
      !isTableStart(lines, index) &&
      !/^-\s+/.test(lines[index].trim())
    ) {
      paragraph.push(lines[index].trim());
      index += 1;
    }
    html.push(`<p>${renderInline(paragraph.join(" "))}</p>`);
  }

  return html.join("");
}

function isTableStart(lines, index) {
  return isTableLine(lines[index]) && index + 1 < lines.length && /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(lines[index + 1]);
}

function isTableLine(line) {
  const trimmed = String(line || "").trim();
  return trimmed.startsWith("|") && trimmed.endsWith("|") && trimmed.includes("|");
}

function renderTable(tableLines) {
  const rows = tableLines
    .filter((line, index) => index !== 1)
    .map((line) => line.trim().slice(1, -1).split("|").map((cell) => cell.trim()));
  if (!rows.length) return "";

  const header = rows[0];
  const body = rows.slice(1);
  const headHtml = header.map((cell) => `<th>${renderInline(cell)}</th>`).join("");
  const bodyHtml = body
    .map((row) => `<tr>${row.map((cell) => `<td>${renderInline(shortenProductCell(cell))}</td>`).join("")}</tr>`)
    .join("");

  return `<div class="table-scroll"><table><thead><tr>${headHtml}</tr></thead><tbody>${bodyHtml}</tbody></table></div>`;
}

function shortenProductCell(cell) {
  const link = /^\[(.+?)\]\((https?:\/\/[^)]+)\)$/.exec(cell);
  if (!link) return cell;
  return `[${link[1]}](${link[2]})`;
}

function renderInline(text) {
  const parts = [];
  const pattern = /\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g;
  let lastIndex = 0;
  let match;
  while ((match = pattern.exec(text)) !== null) {
    parts.push(escapeHtml(text.slice(lastIndex, match.index)));
    const label = normalizeLinkLabel(match[1], match[2]);
    parts.push(`<a href="${escapeAttribute(match[2])}" title="${escapeAttribute(match[2])}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>`);
    lastIndex = pattern.lastIndex;
  }
  parts.push(escapeHtml(text.slice(lastIndex)));
  return parts.join("").replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
}

function normalizeLinkLabel(label, url) {
  const text = String(label || "").trim();
  if (/pxb7\.com\/product\//.test(url) && /^\d+$/.test(text)) {
    return `商品 ${text} · 打开`;
  }
  return text || "打开链接";
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function escapeAttribute(text) {
  return String(text || "").replace(/"/g, "&quot;");
}

// Auto-load rules on page load
loadRules();
