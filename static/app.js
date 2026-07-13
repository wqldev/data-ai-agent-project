(() => {
  const STORAGE_KEYS = {
    config: "ai_agent_da_config",
    history: "ai_agent_da_history",
  };

  const els = {
    btnOpenConfig: document.getElementById("btnOpenConfig"),
    btnCloseConfig: document.getElementById("btnCloseConfig"),
    btnCancelConfig: document.getElementById("btnCancelConfig"),
    btnTestApi: document.getElementById("btnTestApi"),
    configModal: document.getElementById("configModal"),
    configForm: document.getElementById("configForm"),
    cfgApiBase: document.getElementById("cfgApiBase"),
    cfgApiKey: document.getElementById("cfgApiKey"),
    cfgModel: document.getElementById("cfgModel"),
    configMsg: document.getElementById("configMsg"),
    questionInput: document.getElementById("questionInput"),
    btnAnalyze: document.getElementById("btnAnalyze"),
    processLog: document.getElementById("processLog"),
    verifyBadge: document.getElementById("verifyBadge"),
    reportCard: document.getElementById("reportCard"),
    reportBody: document.getElementById("reportBody"),
    historyList: document.getElementById("historyList"),
    historyEmpty: document.getElementById("historyEmpty"),
    btnClearHistory: document.getElementById("btnClearHistory"),
  };

  let activeId = null;
  let analyzing = false;

  function loadConfig() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEYS.config) || "null");
    } catch {
      return null;
    }
  }

  function saveConfig(cfg) {
    localStorage.setItem(STORAGE_KEYS.config, JSON.stringify(cfg));
  }

  function loadHistory() {
    try {
      const list = JSON.parse(localStorage.getItem(STORAGE_KEYS.history) || "[]");
      return Array.isArray(list) ? list : [];
    } catch {
      return [];
    }
  }

  function saveHistory(list) {
    localStorage.setItem(STORAGE_KEYS.history, JSON.stringify(list));
  }

  function openConfig(prefill = true) {
    const cfg = loadConfig();
    if (prefill && cfg) {
      els.cfgApiBase.value = cfg.api_base || "";
      els.cfgApiKey.value = cfg.api_key || "";
      els.cfgModel.value = cfg.model || "";
    }
    els.configMsg.textContent = "";
    els.configMsg.className = "form-msg";
    els.configModal.classList.remove("hidden");
  }

  function closeConfig() {
    els.configModal.classList.add("hidden");
  }

  function requireConfig() {
    const cfg = loadConfig();
    if (!cfg?.api_base || !cfg?.api_key || !cfg?.model) {
      openConfig();
      setConfigMsg("请先完成模型配置并保存。", "err");
      return null;
    }
    return cfg;
  }

  function setConfigMsg(text, type = "") {
    els.configMsg.textContent = text;
    els.configMsg.className = `form-msg ${type}`.trim();
  }

  function appendLog(stage, message, isError = false) {
    const line = document.createElement("div");
    line.className = `log-line${isError ? " error" : ""}`;
    line.innerHTML = `<div class="log-stage">${escapeHtml(stage)}</div><div class="log-msg">${escapeHtml(message)}</div>`;
    els.processLog.appendChild(line);
    els.processLog.scrollTop = els.processLog.scrollHeight;
  }

  function clearProcess() {
    els.processLog.innerHTML = "";
    els.verifyBadge.className = "verify-badge hidden";
    els.verifyBadge.textContent = "";
    els.reportCard.className = "report-card hidden";
    els.reportBody.innerHTML = "";
  }

  function setVerifyBadge(passed, score) {
    els.verifyBadge.classList.remove("hidden");
    if (passed) {
      els.verifyBadge.className = "verify-badge pass";
      els.verifyBadge.textContent = `验证通过 · ${Math.round(score)} 分`;
    } else {
      els.verifyBadge.className = "verify-badge fail";
      els.verifyBadge.textContent = `验证未通过 · ${Math.round(score)} 分`;
    }
  }

  function showReport(markdown, passed) {
    els.reportCard.className = `report-card ${passed ? "pass" : "fail"}`;
    els.reportBody.innerHTML = renderMarkdown(markdown || "");
  }

  function escapeHtml(str) {
    return String(str)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  /** Lightweight Markdown → HTML for report display. */
  function renderMarkdown(md) {
    const lines = String(md).replace(/\r\n/g, "\n").split("\n");
    const html = [];
    let inList = false;
    let inCode = false;
    let codeBuf = [];

    const flushList = () => {
      if (inList) {
        html.push("</ul>");
        inList = false;
      }
    };

    for (const raw of lines) {
      if (raw.startsWith("```")) {
        if (inCode) {
          html.push(`<pre><code>${escapeHtml(codeBuf.join("\n"))}</code></pre>`);
          codeBuf = [];
          inCode = false;
        } else {
          flushList();
          inCode = true;
        }
        continue;
      }
      if (inCode) {
        codeBuf.push(raw);
        continue;
      }

      if (/^\s*[-*]\s+/.test(raw)) {
        if (!inList) {
          html.push("<ul>");
          inList = true;
        }
        html.push(`<li>${inlineFormat(raw.replace(/^\s*[-*]\s+/, ""))}</li>`);
        continue;
      }

      flushList();
      if (/^###\s+/.test(raw)) {
        html.push(`<h3>${inlineFormat(raw.replace(/^###\s+/, ""))}</h3>`);
      } else if (/^##\s+/.test(raw)) {
        html.push(`<h2>${inlineFormat(raw.replace(/^##\s+/, ""))}</h2>`);
      } else if (/^#\s+/.test(raw)) {
        html.push(`<h1>${inlineFormat(raw.replace(/^#\s+/, ""))}</h1>`);
      } else if (raw.trim() === "") {
        html.push("");
      } else {
        html.push(`<p>${inlineFormat(raw)}</p>`);
      }
    }
    flushList();
    if (inCode) {
      html.push(`<pre><code>${escapeHtml(codeBuf.join("\n"))}</code></pre>`);
    }
    return html.join("\n");
  }

  function inlineFormat(text) {
    let s = escapeHtml(text);
    s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
    s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    return s;
  }

  function formatTime(ts) {
    const d = new Date(ts);
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  function renderHistory() {
    const list = loadHistory();
    els.historyList.innerHTML = "";
    els.historyEmpty.classList.toggle("hidden", list.length > 0);

    list.forEach((item) => {
      const li = document.createElement("li");
      li.className = `history-item${item.id === activeId ? " active" : ""}`;
      li.dataset.id = item.id;

      const main = document.createElement("div");
      main.className = "history-main";
      main.innerHTML = `
        <p class="history-title" title="${escapeHtml(item.question)}">${escapeHtml(item.question)}</p>
        <p class="history-meta">${formatTime(item.createdAt)} · ${item.passed ? "通过" : "未通过"}</p>
      `;

      const del = document.createElement("button");
      del.type = "button";
      del.className = "history-delete";
      del.title = "删除";
      del.setAttribute("aria-label", "删除任务");
      del.innerHTML = `<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path fill="currentColor" d="M9 3h6l1 2h4v2H4V5h4l1-2zm1 6h2v9h-2V9zm4 0h2v9h-2V9zM7 9h2v9H7V9zm-1 12h12V7H6v14z"/></svg>`;

      del.addEventListener("click", (e) => {
        e.stopPropagation();
        deleteHistory(item.id);
      });

      li.appendChild(main);
      li.appendChild(del);
      li.addEventListener("click", () => restoreHistory(item.id));
      els.historyList.appendChild(li);
    });
  }

  function upsertHistory(entry) {
    const list = loadHistory().filter((x) => x.id !== entry.id);
    list.unshift(entry);
    saveHistory(list.slice(0, 50));
    renderHistory();
  }

  function deleteHistory(id) {
    const list = loadHistory().filter((x) => x.id !== id);
    saveHistory(list);
    if (activeId === id) {
      activeId = null;
      clearProcess();
      els.questionInput.value = "";
    }
    renderHistory();
  }

  function restoreHistory(id) {
    const item = loadHistory().find((x) => x.id === id);
    if (!item) return;
    activeId = id;
    els.questionInput.value = item.question;
    clearProcess();
    (item.logs || []).forEach((log) => appendLog(log.stage, log.message, !!log.error));
    if (typeof item.passed === "boolean") {
      setVerifyBadge(item.passed, item.score ?? 0);
      showReport(item.finalMarkdown || "", item.passed);
    }
    renderHistory();
  }

  async function testApi() {
    const payload = {
      api_base: els.cfgApiBase.value.trim(),
      api_key: els.cfgApiKey.value.trim(),
      model: els.cfgModel.value.trim(),
    };
    if (!payload.api_base || !payload.api_key || !payload.model) {
      setConfigMsg("请先填写 API 地址、Key 和模型名称。", "err");
      return;
    }
    els.btnTestApi.disabled = true;
    setConfigMsg("正在测试连接…");
    try {
      const res = await fetch("/api/test-connection", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || "测试失败");
      }
      setConfigMsg(`连接成功：${data.reply || "OK"}`, "ok");
    } catch (err) {
      setConfigMsg(err.message || String(err), "err");
    } finally {
      els.btnTestApi.disabled = false;
    }
  }

  async function startAnalyze() {
    if (analyzing) return;
    const cfg = requireConfig();
    if (!cfg) return;

    const question = els.questionInput.value.trim();
    if (!question) {
      els.questionInput.focus();
      appendLog("系统", "请输入分析问题。", true);
      return;
    }

    analyzing = true;
    els.btnAnalyze.disabled = true;
    clearProcess();
    appendLog("系统", "已提交问题，启动 Planner → Builder → Verifier …");

    const taskId = `t_${Date.now()}`;
    activeId = taskId;
    const logs = [];
    const recordLog = (stage, message, error = false) => {
      logs.push({ stage, message, error });
      appendLog(stage, message, error);
    };

    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          api_base: cfg.api_base,
          api_key: cfg.api_key,
          model: cfg.model,
        }),
      });

      if (!res.ok || !res.body) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `请求失败 (${res.status})`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const chunks = buffer.split("\n\n");
        buffer = chunks.pop() || "";

        for (const chunk of chunks) {
          const line = chunk.split("\n").find((l) => l.startsWith("data: "));
          if (!line) continue;
          const event = JSON.parse(line.slice(6));
          handleEvent(event, recordLog, question, taskId, logs);
        }
      }
    } catch (err) {
      recordLog("错误", err.message || String(err), true);
    } finally {
      analyzing = false;
      els.btnAnalyze.disabled = false;
    }
  }

  function handleEvent(event, recordLog, question, taskId, logs) {
    if (event.type === "error") {
      recordLog("错误", event.message || "未知错误", true);
      return;
    }

    if (event.type === "rejected") {
      const msg = event.message || "请重新描述您的需求，只支持数据分析类问题。";
      recordLog("提示", msg, true);
      els.verifyBadge.className = "verify-badge fail";
      els.verifyBadge.textContent = "未受理";
      els.reportCard.className = "report-card fail";
      els.reportBody.innerHTML = `<p><strong>${escapeHtml(msg)}</strong></p>`;
      return;
    }

    if (event.type === "stage") {
      const stageLabel = {
        gate: "Gate",
        planner: "Planner",
        builder: "Builder",
        verifier: "Verifier",
      }[event.stage] || event.stage;

      if (event.status === "running") {
        recordLog(stageLabel, event.message || "进行中…");
      } else if (event.status === "done") {
        if (event.stage === "planner" && event.data) {
          const criteria = (event.data.acceptance_criteria || [])
            .map((c) => `${c.id}: ${c.description}`)
            .join("\n");
          recordLog(
            stageLabel,
            `目标：${event.data.goal}\n类型：${event.data.analysis_type}\n子任务：${(event.data.subtasks || []).join("；")}\n接受标准：\n${criteria}`
          );
        } else if (event.stage === "builder" && event.data) {
          recordLog(
            stageLabel,
            `报告已生成：${event.data.title}\n摘要：${event.data.executive_summary}`
          );
        } else if (event.stage === "verifier" && event.data) {
          const checks = (event.data.checks || [])
            .map((c) => `${c.passed ? "✓" : "✗"} ${c.id} ${c.description} — ${c.comment}`)
            .join("\n");
          recordLog(stageLabel, `${event.data.summary}\n${checks}`);
        } else {
          recordLog(stageLabel, event.message || "完成");
        }
      }
      return;
    }

    if (event.type === "final") {
      setVerifyBadge(!!event.passed, event.score ?? 0);
      showReport(event.final_markdown || "", !!event.passed);
      upsertHistory({
        id: taskId,
        question,
        createdAt: Date.now(),
        passed: !!event.passed,
        score: event.score ?? 0,
        finalMarkdown: event.final_markdown || "",
        logs: [...logs],
        plan: event.plan,
        report: event.report,
        verification: event.verification,
      });
    }
  }

  // Events
  els.btnOpenConfig.addEventListener("click", () => openConfig(true));
  els.btnCloseConfig.addEventListener("click", closeConfig);
  els.btnCancelConfig.addEventListener("click", closeConfig);
  els.configModal.addEventListener("click", (e) => {
    if (e.target === els.configModal) closeConfig();
  });
  els.btnTestApi.addEventListener("click", testApi);
  els.configForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const cfg = {
      api_base: els.cfgApiBase.value.trim(),
      api_key: els.cfgApiKey.value.trim(),
      model: els.cfgModel.value.trim(),
    };
    if (!cfg.api_base || !cfg.api_key || !cfg.model) {
      setConfigMsg("请完整填写配置项。", "err");
      return;
    }
    saveConfig(cfg);
    setConfigMsg("已保存到本机浏览器。", "ok");
    setTimeout(closeConfig, 450);
  });
  els.btnAnalyze.addEventListener("click", startAnalyze);
  els.questionInput.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") startAnalyze();
  });
  els.btnClearHistory.addEventListener("click", () => {
    if (!loadHistory().length) return;
    if (confirm("确定清空全部历史任务？")) {
      saveHistory([]);
      activeId = null;
      clearProcess();
      renderHistory();
    }
  });

  // Init
  renderHistory();
  if (!loadConfig()) {
    // Soft prompt on first visit
    setTimeout(() => openConfig(false), 400);
  }
})();
