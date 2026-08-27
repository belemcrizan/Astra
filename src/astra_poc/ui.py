"""Self-contained HTML/CSS/JS frontend for ASTRA v0.4.1 Investigation Service."""

INVESTIGATION_UI_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ASTRA v0.4.1 — Autonomous Investigation Engine</title>
  <style>
    :root {
      --bg: #0b0f19;
      --card-bg: #121826;
      --card-border: #1f293d;
      --text: #f1f5f9;
      --text-muted: #94a3b8;
      --primary: #3b82f6;
      --primary-hover: #2563eb;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --accent: #8b5cf6;
      --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      line-height: 1.5;
      padding: 24px;
    }
    .container { max-width: 1200px; margin: 0 auto; }
    header {
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 20px;
      margin-bottom: 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
    }
    .logo-area h1 { font-size: 28px; font-weight: 800; letter-spacing: -0.5px; color: #fff; }
    .logo-area h1 span { color: var(--primary); }
    .tagline { color: var(--text-muted); font-size: 14px; margin-top: 4px; }
    .badges { display: flex; gap: 8px; flex-wrap: wrap; }
    .badge {
      font-size: 12px;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 9999px;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .badge.live::before {
      content: "";
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--success);
      box-shadow: 0 0 8px var(--success);
    }
    .control-panel {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 18px 24px;
      margin-bottom: 24px;
      display: flex;
      align-items: center;
      gap: 16px;
      flex-wrap: wrap;
    }
    .control-panel label { font-size: 14px; font-weight: 600; color: var(--text-muted); }
    select, button {
      background: #1e293b;
      color: #fff;
      border: 1px solid var(--card-border);
      padding: 10px 16px;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
    }
    select:focus, button:focus { outline: 2px solid var(--primary); }
    button.btn-primary {
      background: var(--primary);
      border-color: var(--primary);
      transition: background 0.15s;
    }
    button.btn-primary:hover { background: var(--primary-hover); }
    button:disabled { opacity: 0.5; cursor: not-allowed; }
    .loading-status {
      display: none;
      align-items: center;
      gap: 10px;
      color: var(--primary);
      font-size: 14px;
      font-weight: 600;
    }
    .spinner {
      width: 16px;
      height: 16px;
      border: 2px solid var(--primary);
      border-top-color: transparent;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .grid-2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
      margin-bottom: 24px;
    }
    @media (max-width: 860px) { .grid-2 { grid-template-columns: 1fr; } }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 20px;
    }
    .card-title {
      font-size: 16px;
      font-weight: 700;
      color: #fff;
      margin-bottom: 14px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    canvas {
      width: 100%;
      height: 180px;
      background: #0f172a;
      border-radius: 8px;
      border: 1px solid var(--card-border);
    }
    .hypothesis-list { display: flex; flex-direction: column; gap: 10px; }
    .hypothesis-item {
      background: #0f172a;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 10px 14px;
    }
    .hypothesis-header {
      display: flex;
      justify-content: space-between;
      font-size: 13px;
      font-weight: 600;
      margin-bottom: 6px;
    }
    .progress-bg {
      background: #1e293b;
      height: 8px;
      border-radius: 4px;
      overflow: hidden;
    }
    .progress-bar {
      height: 100%;
      background: var(--primary);
      border-radius: 4px;
      transition: width 0.4s ease;
    }
    .progress-bar.falsified { background: #64748b; }
    .progress-bar.supported { background: var(--success); }
    .progress-bar.unknown { background: var(--accent); }
    .decision-panel {
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .decision-banner {
      padding: 16px;
      border-radius: 8px;
      text-align: center;
      font-size: 24px;
      font-weight: 800;
      letter-spacing: 1px;
    }
    .decision-banner.ESCALATE { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }
    .decision-banner.CLOSE { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }
    .decision-banner.DEFER { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }
    .decision-banner.WATCH { background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.4); }
    .info-row {
      display: flex;
      justify-content: space-between;
      font-size: 13px;
      padding: 6px 0;
      border-bottom: 1px solid #1e293b;
    }
    .info-label { color: var(--text-muted); font-weight: 600; }
    .info-val { font-weight: 600; text-align: right; }
    .timeline {
      display: flex;
      flex-direction: column;
      gap: 16px;
      margin-top: 10px;
    }
    .turn-card {
      background: #0f172a;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 14px 18px;
    }
    .turn-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
    }
    .turn-title { font-size: 14px; font-weight: 700; color: #fff; }
    .val-badge {
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 4px;
      font-weight: 700;
    }
    .val-badge.passed { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #059669; }
    .val-badge.rejected { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #dc2626; }
    .proposal-box {
      background: #1e293b;
      border-left: 3px solid var(--primary);
      padding: 8px 12px;
      border-radius: 4px;
      font-size: 13px;
      margin-bottom: 8px;
    }
    .evidence-box {
      background: #1e293b;
      border-left: 3px solid var(--success);
      padding: 8px 12px;
      border-radius: 4px;
      font-size: 13px;
    }
    .audit-box {
      font-family: var(--font-mono);
      font-size: 12px;
      background: #0f172a;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 14px;
      word-break: break-all;
    }
    .copy-btn {
      background: #334155;
      font-size: 11px;
      padding: 4px 8px;
      margin-left: 8px;
      border-radius: 4px;
    }
    footer {
      border-top: 1px solid var(--card-border);
      margin-top: 36px;
      padding-top: 20px;
      color: var(--text-muted);
      font-size: 13px;
      display: flex;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 12px;
    }
    details { margin-top: 16px; font-size: 13px; color: var(--text-muted); }
    summary { cursor: pointer; font-weight: 600; color: var(--text); padding: 4px 0; }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="logo-area">
        <h1>ASTRA <span>v0.4.1</span></h1>
        <div class="tagline">Bounded Autonomous Investigation Engine for Weak Signals and Regime Shifts</div>
      </div>
      <div class="badges">
        <span class="badge live" id="badge-runtime">Google Cloud Run</span>
        <span class="badge" id="badge-adk">Google ADK 2.8</span>
        <span class="badge" id="badge-model">Gemini 3.5+</span>
        <span class="badge" id="badge-dsl">ASTRA Restricted DSL</span>
      </div>
    </header>

    <div class="control-panel">
      <label for="scenario-select">Investigation Scenario:</label>
      <select id="scenario-select">
        <option value="hero">Hero: Abrupt Regime Break (Family C)</option>
        <option value="control">Control: Benign Fluctuation Safe Closure (Family A)</option>
        <option value="unknown">Unknown: Heavy-Tailed Open Set (Family H)</option>
        <option value="adversarial">Adversarial: Impulse Burst Stress (Family I)</option>
      </select>
      <button class="btn-primary" id="btn-run" onclick="runInvestigation()">Run Investigation</button>
      <div class="loading-status" id="loading-indicator">
        <div class="spinner"></div>
        <span id="loading-msg">Engaging Google ADK & Gemini 3.5+...</span>
      </div>
    </div>

    <div class="grid-2">
      <!-- Observed Signal -->
      <div class="card">
        <div class="card-title">
          <span>Observed Signal Stream</span>
          <span style="font-size: 12px; color: var(--danger);">Trigger: t=600</span>
        </div>
        <canvas id="signalCanvas" width="540" height="180"></canvas>
        <div style="font-size: 12px; color: var(--text-muted); margin-top: 8px;">
          Time series with stationary background variance and triggered anomaly spike.
        </div>
      </div>

      <!-- Competing Hypotheses -->
      <div class="card">
        <div class="card-title">
          <span>Active Competing Hypotheses</span>
          <span style="font-size: 12px; color: var(--text-muted);">Evidence-Ranked</span>
        </div>
        <div class="hypothesis-list" id="hypothesis-list">
          <div class="hypothesis-item">
            <div class="hypothesis-header"><span>H1: Transient Fluctuation</span><span>25.0%</span></div>
            <div class="progress-bg"><div class="progress-bar" style="width: 25%;"></div></div>
          </div>
          <div class="hypothesis-item">
            <div class="hypothesis-header"><span>H2: Volatility Clustering</span><span>25.0%</span></div>
            <div class="progress-bg"><div class="progress-bar" style="width: 25%;"></div></div>
          </div>
          <div class="hypothesis-item">
            <div class="hypothesis-header"><span>H3: Structural Regime Shift</span><span>25.0%</span></div>
            <div class="progress-bg"><div class="progress-bar" style="width: 25%;"></div></div>
          </div>
          <div class="hypothesis-item">
            <div class="hypothesis-header"><span>H4: Periodic Pattern</span><span>25.0%</span></div>
            <div class="progress-bg"><div class="progress-bar" style="width: 25%;"></div></div>
          </div>
          <div class="hypothesis-item">
            <div class="hypothesis-header"><span>H_unknown: Unmodeled Dynamics</span><span>20.0%</span></div>
            <div class="progress-bg"><div class="progress-bar unknown" style="width: 20%;"></div></div>
          </div>
        </div>
      </div>
    </div>

    <div class="grid-2">
      <!-- Final Decision -->
      <div class="card decision-panel">
        <div class="card-title">Final Investigation Decision</div>
        <div class="decision-banner ESCALATE" id="decision-banner">ESCALATE</div>
        <div class="info-row">
          <span class="info-label">Stop Reason</span>
          <span class="info-val" id="val-stop-reason">DECISION_SUFFICIENT</span>
        </div>
        <div class="info-row">
          <span class="info-label">Operational Reliability Score</span>
          <span class="info-val" id="val-reliability" title="Operational score used by ASTRA decision policy, not a posterior probability.">0.775</span>
        </div>
        <div class="info-row">
          <span class="info-label">Primary Rationale</span>
          <span class="info-val" id="val-primary-reason">Structural Regime Shift supported by multiple discriminative tests.</span>
        </div>
        <div class="info-row">
          <span class="info-label">Execution Duration</span>
          <span class="info-val" id="val-duration">248 ms</span>
        </div>
      </div>

      <!-- Counterfactuals & Boundaries -->
      <div class="card">
        <div class="card-title">Counterfactual Decision Boundaries</div>
        <div id="counterfactual-list" style="font-size: 13px; display: flex; flex-direction: column; gap: 8px;">
          <div style="background: #0f172a; padding: 10px; border-radius: 6px; border-left: 3px solid var(--primary);">
            <b>WATCH:</b> If H2 evidence score had remained below 0.65.
          </div>
          <div style="background: #0f172a; padding: 10px; border-radius: 6px; border-left: 3px solid var(--warning);">
            <b>DEFER:</b> If H_unknown score exceeded 0.60.
          </div>
        </div>
      </div>
    </div>

    <!-- Investigation Timeline -->
    <div class="card" style="margin-bottom: 24px;">
      <div class="card-title">
        <span>Investigation Timeline (Google ADK Proposal → ASTRA Restricted DSL Execution)</span>
        <span style="font-size: 12px; color: var(--text-muted);" id="val-turn-count">3 Diagnostic Turns</span>
      </div>
      <div class="timeline" id="timeline-container">
        <!-- Turns dynamically rendered here -->
      </div>
    </div>

    <!-- Audit & Cryptographic Trace -->
    <div class="card">
      <div class="card-title">
        <span>Cryptographic Audit Trail</span>
        <button class="copy-btn" onclick="copyTrace()">Copy Trace ID</button>
      </div>
      <div class="audit-box" id="audit-box">
        Trace ID: <span id="val-trace-id">trace-90513d038d4a</span><br>
        Case ID: <span id="val-case-id">cloud-case-hero-42</span><br>
        Framework: <span id="val-framework">Google ADK 2.8</span> | Model: <span id="val-model-name">gemini-3.5-flash-lite</span><br>
        Boundary: ASTRA Restricted DSL (Deterministic Kernel Sandbox)<br>
        Executed Operations: <span id="val-ops">COMPARE_WINDOWS, RUN_PELT</span>
      </div>
      <details>
        <summary>View Complete JSON Response Payload</summary>
        <pre id="raw-json" style="background:#0f172a; padding:12px; border-radius:6px; margin-top:8px; overflow-x:auto; font-size:11px;"></pre>
      </details>
    </div>

    <footer>
      <div>ASTRA v0.4.1 — Evidence-Driven Autonomous Investigation Engine</div>
      <div>Google Hackathon Submission | Gemini 3.5+ + Google ADK + Google Cloud Run</div>
    </footer>
  </div>

  <script>
    let currentTraceId = "";

    function drawChart(dataPoints) {
      const canvas = document.getElementById("signalCanvas");
      const ctx = canvas.getContext("2d");
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      if (!dataPoints || dataPoints.length === 0) {
        dataPoints = Array.from({length: 120}, (_, i) => (Math.random() - 0.5) * (i > 60 ? 0.04 : 0.01));
      }

      const w = canvas.width;
      const h = canvas.height;
      const min = Math.min(...dataPoints);
      const max = Math.max(...dataPoints);
      const range = (max - min) || 1;

      // Draw zero line
      const zeroY = h - ((0 - min) / range) * h;
      ctx.strokeStyle = "#334155";
      ctx.beginPath();
      ctx.moveTo(0, zeroY);
      ctx.lineTo(w, zeroY);
      ctx.stroke();

      // Draw Trigger Line at middle
      const trigX = w / 2;
      ctx.strokeStyle = "rgba(239, 68, 68, 0.7)";
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(trigX, 0);
      ctx.lineTo(trigX, h);
      ctx.stroke();
      ctx.setLineDash([]);

      // Draw Signal Series
      ctx.strokeStyle = "#38bdf8";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      for (let i = 0; i < dataPoints.length; i++) {
        const x = (i / (dataPoints.length - 1)) * w;
        const y = h - ((dataPoints[i] - min) / range) * (h - 20) - 10;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    }

    async function runInvestigation() {
      const scenario = document.getElementById("scenario-select").value;
      const btn = document.getElementById("btn-run");
      const loading = document.getElementById("loading-indicator");

      btn.disabled = true;
      loading.style.display = "flex";

      try {
        const res = await fetch("/agent/investigate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ scenario: scenario, seed: 42, max_turns: 4 })
        });

        if (!res.ok) throw new Error("Server returned " + res.status);
        const data = await res.json();
        renderResult(data);
      } catch (err) {
        alert("Investigation error: " + err.message);
      } finally {
        btn.disabled = false;
        loading.style.display = "none";
      }
    }

    function renderResult(data) {
      currentTraceId = data.trace_id || "";

      // Update Header Badges & Runtime
      document.getElementById("badge-runtime").textContent = data.runtime || "Google Cloud Run";
      document.getElementById("badge-adk").textContent = data.agent_framework || "Google ADK";
      document.getElementById("badge-model").textContent = data.model || "Gemini 3.5+";

      // Draw Chart
      if (data.series_preview) {
        drawChart(data.series_preview);
      }

      // Update Hypotheses
      const hypList = document.getElementById("hypothesis-list");
      hypList.innerHTML = "";
      (data.competing_hypotheses || []).forEach(h => {
        const scorePct = (h.score * 100).toFixed(1);
        let barClass = "";
        if (h.status === "FALSIFIED") barClass = "falsified";
        else if (h.status === "SUPPORTED") barClass = "supported";
        else if (h.id.includes("unknown")) barClass = "unknown";

        hypList.innerHTML += `
          <div class="hypothesis-item">
            <div class="hypothesis-header">
              <span>${h.id}: ${h.name} (${h.status})</span>
              <span>${scorePct}%</span>
            </div>
            <div class="progress-bg"><div class="progress-bar ${barClass}" style="width: ${scorePct}%;"></div></div>
          </div>
        `;
      });

      // Update Decision Panel
      const dec = data.decision || "UNKNOWN";
      const banner = document.getElementById("decision-banner");
      banner.textContent = dec;
      banner.className = "decision-banner " + dec;

      document.getElementById("val-stop-reason").textContent = data.stop_reason || "";
      document.getElementById("val-reliability").textContent = (data.decision_reliability_score !== undefined ? data.decision_reliability_score : "0.775");
      document.getElementById("val-primary-reason").textContent = data.primary_reason || "";
      document.getElementById("val-duration").textContent = (data.duration_ms || 250) + " ms";

      // Update Counterfactuals
      const cfList = document.getElementById("counterfactual-list");
      cfList.innerHTML = "";
      (data.counterfactuals || []).forEach(cf => {
        cfList.innerHTML += `
          <div style="background: #0f172a; padding: 10px; border-radius: 6px; border-left: 3px solid var(--primary);">
            <b>${cf.target_decision}:</b> ${cf.condition}
          </div>
        `;
      });

      // Update Timeline
      const timeline = document.getElementById("timeline-container");
      timeline.innerHTML = "";
      const provs = data.provenance_records || [];
      document.getElementById("val-turn-count").textContent = `${provs.length} Diagnostic Turns`;

      provs.forEach((p, idx) => {
        const valPassed = p.astra_validation_passed;
        const valClass = valPassed ? "passed" : "rejected";
        const valText = valPassed ? "DSL VALIDATION: PASSED" : ("REJECTED: " + p.validation_error);

        let evHtml = "";
        (p.evidence_generated || []).forEach(e => {
          evHtml += `<div>• ${e.statement || JSON.stringify(e)}</div>`;
        });

        timeline.innerHTML += `
          <div class="turn-card">
            <div class="turn-header">
              <span class="turn-title">Turn ${p.turn || (idx + 1)}: ${p.proposal.proposed_operation}</span>
              <span class="val-badge ${valClass}">${valText}</span>
            </div>
            <div class="proposal-box">
              <b>AI Proposal (${p.agent_framework} + ${p.model}):</b> ${p.proposal.goal}<br>
              <span style="color:var(--text-muted); font-size:12px;">Rationale: ${p.proposal.rationale}</span>
            </div>
            <div class="evidence-box">
              <b>ASTRA Verified Evidence:</b>
              ${evHtml || "No evidence recorded."}
            </div>
          </div>
        `;
      });

      // Update Audit
      document.getElementById("val-trace-id").textContent = data.trace_id || "";
      document.getElementById("val-case-id").textContent = data.case_id || "";
      document.getElementById("val-framework").textContent = data.agent_framework || "";
      document.getElementById("val-model-name").textContent = data.model || "";
      document.getElementById("val-ops").textContent = (data.executed_operations || []).join(", ");
      document.getElementById("raw-json").textContent = JSON.stringify(data, null, 2);
    }

    function copyTrace() {
      if (currentTraceId) {
        navigator.clipboard.writeText(currentTraceId);
        alert("Trace ID copied: " + currentTraceId);
      }
    }

    // Initialize initial view
    window.addEventListener("DOMContentLoaded", () => {
      drawChart();
      runInvestigation();
    });
  </script>
</body>
</html>
"""
