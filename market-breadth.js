const MARKET_BREADTH_HOST_ID = "market-breadth-host";
const MARKET_BREADTH_STYLE_ID = "market-breadth-style";
const MARKET_BREADTH_REFRESH_MS = 10 * 60 * 1000;
const MARKET_BREADTH_BASELINE = 3000;
let marketBreadthRefreshInFlight = false;

function ensureMarketBreadthStyle() {
  if (document.getElementById(MARKET_BREADTH_STYLE_ID)) return;

  const style = document.createElement("style");
  style.id = MARKET_BREADTH_STYLE_ID;
  style.textContent = `
    .market-breadth-board{margin-top:22px;padding:22px;border:1px solid rgba(255,255,255,.08);border-radius:24px;background:linear-gradient(135deg,rgba(115,197,255,.08),transparent 55%),#0c1019d1;backdrop-filter:blur(18px);box-shadow:var(--shadow)}
    .market-breadth-header{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;flex-wrap:wrap}
    .market-breadth-header h2{margin:8px 0 0;font-size:clamp(1.6rem,2.2vw,2.2rem);line-height:1.08}
    .market-breadth-caption{margin:0;max-width:36rem;color:var(--muted);font-size:.92rem;line-height:1.55}
    .market-breadth-signal{display:inline-flex;align-items:center;gap:8px;padding:8px 12px;border-radius:999px;border:1px solid transparent;font-family:Trebuchet MS,sans-serif;font-size:.8rem;letter-spacing:.04em;white-space:nowrap}
    .market-breadth-signal.positive{color:var(--green);background:rgba(75,208,138,.12);border-color:rgba(75,208,138,.28)}
    .market-breadth-signal.alert{color:var(--gold);background:rgba(245,183,58,.12);border-color:rgba(245,183,58,.28)}
    .market-breadth-signal.negative{color:var(--red);background:rgba(245,109,112,.12);border-color:rgba(245,109,112,.28)}
    .market-breadth-grid{margin-top:16px;display:grid;grid-template-columns:minmax(0,1.7fr) minmax(300px,1fr);gap:16px}
    .market-breadth-chart-card,.market-breadth-metrics{padding:16px;border-radius:18px;border:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.04)}
    .market-breadth-chart{width:100%;height:240px;display:block}
    .market-breadth-axis-text,.market-breadth-x-text,.market-breadth-baseline-text{fill:rgba(245,237,215,.64);font-size:10px;font-family:Trebuchet MS,sans-serif}
    .market-breadth-grid-line{stroke:rgba(255,255,255,.08);stroke-width:1}
    .market-breadth-baseline{stroke:rgba(245,183,58,.85);stroke-width:1.6;stroke-dasharray:5 4}
    .market-breadth-line-main{fill:none;stroke:#4bd08a;stroke-width:3.2;stroke-linejoin:round;stroke-linecap:round}
    .market-breadth-end-main{stroke:#0c1019;stroke-width:2;fill:#4bd08a}
    .market-breadth-legend{margin-top:12px;display:flex;flex-wrap:wrap;gap:10px}
    .market-breadth-legend-chip{display:inline-flex;align-items:center;gap:8px;padding:7px 10px;border-radius:999px;border:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.06);font-family:Trebuchet MS,sans-serif;font-size:.76rem;color:var(--text)}
    .market-breadth-legend-line{width:18px;height:3px;border-radius:999px;display:inline-block}
    .market-breadth-legend-line.main{background:#4bd08a}
    .market-breadth-legend-line.base{background:#f5b73a}
    .market-breadth-metric-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
    .market-breadth-metric{padding:14px;border-radius:16px;border:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.05)}
    .market-breadth-metric label{display:block;color:var(--muted);font-size:.78rem;letter-spacing:.08em;text-transform:uppercase;font-family:Trebuchet MS,sans-serif}
    .market-breadth-metric strong{display:block;margin-top:8px;font-size:1.45rem;line-height:1}
    .market-breadth-metric span{display:block;margin-top:8px;color:#d8cfb8;font-size:.86rem;line-height:1.45}
    .market-breadth-note{margin:14px 0 0;color:#d8cfb8;font-size:.92rem;line-height:1.6}
    .market-breadth-empty{margin-top:14px;padding:16px;border-radius:18px;border:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.04);color:var(--muted)}
    @media (max-width:960px){.market-breadth-grid{grid-template-columns:1fr}}
  `;
  document.head.appendChild(style);
}

function formatNumber(value) {
  if (!Number.isFinite(value)) return "--";
  return new Intl.NumberFormat("zh-CN").format(value);
}

function formatSignedNumber(value) {
  if (!Number.isFinite(value)) return "--";
  return `${value > 0 ? "+" : ""}${formatNumber(value)}`;
}

function pickTone(label) {
  if (label.includes("反转") || label.includes("回暖")) return "positive";
  if (label.includes("冰点")) return "alert";
  return "negative";
}

function buildDerivedSignal(points) {
  if (!points.length) {
    return {
      label: "暂无宽度数据",
      summary: "当前还没有可用的上涨家数曲线。"
    };
  }

  const upValues = points.map((point) => point.totalUp);
  const latestUp = upValues[upValues.length - 1];
  const lowUp = Math.min(...upValues);
  const rebound = latestUp - lowUp;
  const deviation = latestUp - MARKET_BREADTH_BASELINE;

  if (lowUp <= 1600 && rebound >= 900 && latestUp >= 2600) {
    return {
      label: "冰点反转观察",
      summary: `日内最低上涨家数 ${formatNumber(lowUp)}，当前已从低点修复 ${formatSignedNumber(rebound)}，并重新接近 3000 基准线，可以重点观察反转延续。`
    };
  }

  if (lowUp <= 1800 && rebound >= 500) {
    return {
      label: "冰点修复",
      summary: `日内最低上涨家数 ${formatNumber(lowUp)}，当前修复 ${formatSignedNumber(rebound)}，但还没有真正站稳 3000 基准线，更适合继续观察修复力度。`
    };
  }

  if (latestUp < 1800) {
    return {
      label: "冰点区间",
      summary: `当前上涨家数只有 ${formatNumber(latestUp)}，低于 3000 基准线 ${formatSignedNumber(deviation)}，更接近冰点环境。`
    };
  }

  if (latestUp >= MARKET_BREADTH_BASELINE) {
    return {
      label: "站上基准线",
      summary: `当前上涨家数 ${formatNumber(latestUp)}，高于 3000 基准线 ${formatSignedNumber(deviation)}，市场温度明显回暖。`
    };
  }

  return {
    label: "弱修复观察",
    summary: `当前上涨家数 ${formatNumber(latestUp)}，距离 3000 基准线还差 ${formatSignedNumber(deviation)}，先看能否继续抬升。`
  };
}

function normalizeTrendPoints(profile) {
  const points = Array.isArray(profile?.trendPoints) ? profile.trendPoints : [];
  return points.map((point) => ({
    timestamp: String(point?.timestamp ?? "").trim(),
    totalUp: Number(point?.totalUp ?? 0),
    limitUp: Number(point?.limitUp ?? 0),
    limitDown: Number(point?.limitDown ?? 0),
    flatCount: Number(point?.flatCount ?? 0)
  })).filter((point) => point.timestamp);
}

async function loadSnapshot() {
  if (typeof window !== "undefined" && window.__TAURI_INTERNALS__?.invoke) {
    return window.__TAURI_INTERNALS__.invoke("get_dashboard_snapshot");
  }

  const candidates = [
    "./src/data/akshare-snapshot.json",
    "../src/data/akshare-snapshot.json",
    "/src/data/akshare-snapshot.json"
  ];

  let lastError = null;
  for (const candidate of candidates) {
    try {
      const response = await fetch(`${candidate}?ts=${Date.now()}`, { cache: "no-store" });
      if (!response.ok) {
        lastError = new Error(`快照读取失败：${response.status}`);
        continue;
      }
      return response.json();
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError ?? new Error("快照读取失败");
}

function buildChartSvg(points) {
  const width = 760;
  const height = 240;
  const padding = { top: 20, right: 14, bottom: 28, left: 52 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const values = points.map((point) => point.totalUp).concat(MARKET_BREADTH_BASELINE);
  const minValue = Math.max(0, Math.min(...values) - 250);
  const maxValue = Math.max(...values) + 250;
  const range = Math.max(1, maxValue - minValue);
  const yFor = (value) => padding.top + plotHeight - ((value - minValue) / range) * plotHeight;
  const xFor = (index) => padding.left + (points.length === 1 ? plotWidth / 2 : (index / (points.length - 1)) * plotWidth);
  const polyline = points.map((point, index) => `${xFor(index).toFixed(1)},${yFor(point.totalUp).toFixed(1)}`).join(" ");
  const ticks = [minValue, Math.round((minValue + maxValue) / 2), maxValue];
  const xTickIndexes = Array.from(new Set([0, Math.floor(points.length / 2), points.length - 1]));
  const baselineY = yFor(MARKET_BREADTH_BASELINE).toFixed(1);
  const latest = points[points.length - 1];

  return `
    <svg class="market-breadth-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="A股上涨家数曲线">
      ${ticks.map((value) => {
        const y = yFor(value).toFixed(1);
        return `<line class="market-breadth-grid-line" x1="${padding.left}" y1="${y}" x2="${width - padding.right}" y2="${y}"></line><text class="market-breadth-axis-text" x="${padding.left - 8}" y="${Number(y) + 4}" text-anchor="end">${formatNumber(Math.round(value))}</text>`;
      }).join("")}
      <line class="market-breadth-baseline" x1="${padding.left}" y1="${baselineY}" x2="${width - padding.right}" y2="${baselineY}"></line>
      <text class="market-breadth-baseline-text" x="${width - padding.right - 4}" y="${Number(baselineY) - 6}" text-anchor="end">基准线 3000</text>
      <polyline class="market-breadth-line-main" points="${polyline}"></polyline>
      <circle class="market-breadth-end-main" cx="${xFor(points.length - 1).toFixed(1)}" cy="${yFor(latest.totalUp).toFixed(1)}" r="4.8"></circle>
      ${xTickIndexes.map((index) => `<text class="market-breadth-x-text" x="${xFor(index).toFixed(1)}" y="${height - 8}" text-anchor="middle">${points[index].timestamp}</text>`).join("")}
    </svg>
  `;
}

function buildBoardMarkup(profile) {
  const points = normalizeTrendPoints(profile);
  if (!points.length) {
    return `<div class="market-breadth-header"><div><p class="section-label">Market Breadth</p><h2>A股上涨家数曲线</h2></div></div><div class="market-breadth-empty">暂时还没有可用的上涨家数曲线。</div>`;
  }

  const upValues = points.map((point) => point.totalUp);
  const latest = points[points.length - 1];
  const lowUp = Math.min(...upValues);
  const highUp = Math.max(...upValues);
  const rebound = latest.totalUp - lowUp;
  const deviation = latest.totalUp - MARKET_BREADTH_BASELINE;
  const signal = buildDerivedSignal(points);
  const updatedAt = profile?.updatedAt || profile?.tradeDate || "--";

  return `
    <div class="market-breadth-header">
      <div>
        <p class="section-label">Market Breadth</p>
        <h2>A股上涨家数曲线</h2>
        <p class="market-breadth-caption">只看沪深个股上涨家数，一根曲线，3000 作为情绪基准线。低于它偏冷，重新抬回去更容易看到冰点修复和冰点反转；桌面端每 10 分钟自动刷新一次。</p>
      </div>
      <div class="market-breadth-signal ${pickTone(signal.label)}"><span>${signal.label}</span><span>${updatedAt}</span></div>
    </div>
    <div class="market-breadth-grid">
      <div class="market-breadth-chart-card">
        ${buildChartSvg(points)}
        <div class="market-breadth-legend">
          <span class="market-breadth-legend-chip"><span class="market-breadth-legend-line main"></span>当前上涨家数 ${formatNumber(latest.totalUp)}</span>
          <span class="market-breadth-legend-chip"><span class="market-breadth-legend-line base"></span>情绪基准线 3000</span>
          <span class="market-breadth-legend-chip">相对基准线 ${formatSignedNumber(deviation)}</span>
          <span class="market-breadth-legend-chip">低点修复 ${formatSignedNumber(rebound)}</span>
        </div>
      </div>
      <div class="market-breadth-metrics">
        <div class="market-breadth-metric-grid">
          <div class="market-breadth-metric"><label>当前上涨家数</label><strong>${formatNumber(latest.totalUp)}</strong><span>用一根线直接看市场温度，不再混入下跌线。</span></div>
          <div class="market-breadth-metric"><label>相对 3000</label><strong>${formatSignedNumber(deviation)}</strong><span>高于 3000 更像回暖，低于 3000 更像偏冷环境。</span></div>
          <div class="market-breadth-metric"><label>日内低点</label><strong>${formatNumber(lowUp)}</strong><span>从最低点往上抬升，最有助于观察冰点修复。</span></div>
          <div class="market-breadth-metric"><label>日内高点</label><strong>${formatNumber(highUp)}</strong><span>可以用来判断今天修复是否有持续性。</span></div>
          <div class="market-breadth-metric"><label>涨停 / 跌停</label><strong>${formatNumber(latest.limitUp)} / ${formatNumber(latest.limitDown)}</strong><span>辅助确认情绪有没有真正共振。</span></div>
          <div class="market-breadth-metric"><label>观察结论</label><strong>${signal.label}</strong><span>核心看能否从低位持续靠近并站回 3000 基准线。</span></div>
        </div>
        <p class="market-breadth-note">${signal.summary}</p>
      </div>
    </div>
  `;
}

function ensureMountHost() {
  const appShell = document.querySelector(".app-shell");
  if (!appShell) return null;

  let host = document.getElementById(MARKET_BREADTH_HOST_ID);
  if (!host) {
    host = document.createElement("section");
    host.id = MARKET_BREADTH_HOST_ID;
    host.className = "market-breadth-board";
  }

  const marketStrip = appShell.querySelector(".market-strip");
  if (marketStrip) {
    if (marketStrip.nextSibling !== host) marketStrip.insertAdjacentElement("afterend", host);
  } else if (appShell.firstChild !== host) {
    appShell.prepend(host);
  }

  return host;
}

async function renderMarketBreadth(snapshotOverride = null) {
  ensureMarketBreadthStyle();
  const host = ensureMountHost();
  if (!host) return;

  try {
    const snapshot = snapshotOverride ?? await loadSnapshot();
    const profile = snapshot?.marketRadar?.marketBreadth ?? null;
    host.innerHTML = buildBoardMarkup(profile);
  } catch (error) {
    host.innerHTML = `<div class="market-breadth-header"><div><p class="section-label">Market Breadth</p><h2>A股上涨家数曲线</h2></div></div><div class="market-breadth-empty">市场宽度读取失败：${String(error)}</div>`;
  }
}

async function refreshMarketBreadthPanel() {
  if (document.hidden) return;

  if (typeof window !== "undefined" && window.__TAURI_INTERNALS__?.invoke) {
    if (marketBreadthRefreshInFlight) return;
    marketBreadthRefreshInFlight = true;

    try {
      const snapshot = await window.__TAURI_INTERNALS__.invoke("refresh_market_breadth_snapshot");
      await renderMarketBreadth(snapshot);
      return;
    } catch (error) {
      console.error("market breadth refresh failed", error);
    } finally {
      marketBreadthRefreshInFlight = false;
    }
  }

  await renderMarketBreadth();
}

function startMarketBreadthRuntime() {
  renderMarketBreadth();
  window.setInterval(() => {
    refreshMarketBreadthPanel();
  }, MARKET_BREADTH_REFRESH_MS);

  const observer = new MutationObserver(() => {
    ensureMountHost();
  });
  observer.observe(document.body, { childList: true, subtree: true });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", startMarketBreadthRuntime, { once: true });
} else {
  startMarketBreadthRuntime();
}
