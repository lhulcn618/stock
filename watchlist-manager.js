const WATCHLIST_MANAGER_STYLE_ID = "watchlist-manager-style";
const WATCHLIST_MANAGER_BUTTON_ID = "watchlist-manager-button";
const WATCHLIST_MANAGER_MODAL_ID = "watchlist-manager-modal";

let watchlistMonitorTimer = null;

function isTauriRuntime() {
  return typeof window !== "undefined" && !!window.__TAURI_INTERNALS__?.invoke;
}

async function invokeTauri(command, args = {}) {
  return window.__TAURI_INTERNALS__.invoke(command, args);
}

function ensureWatchlistManagerStyle() {
  if (document.getElementById(WATCHLIST_MANAGER_STYLE_ID)) return;

  const style = document.createElement("style");
  style.id = WATCHLIST_MANAGER_STYLE_ID;
  style.textContent = `
    .watchlist-manager-button{position:fixed;right:22px;bottom:24px;z-index:70;display:inline-flex;align-items:center;gap:8px;padding:12px 16px;border:1px solid rgba(115,197,255,.35);border-radius:999px;background:rgba(12,16,25,.92);color:#d8ecff;font:inherit;cursor:pointer;box-shadow:0 14px 38px rgba(0,0,0,.28);backdrop-filter:blur(16px)}
    .watchlist-manager-button:hover{transform:translateY(-1px);border-color:rgba(115,197,255,.55)}
    .watchlist-manager-button strong{font-size:.95rem}
    .watchlist-manager-backdrop{position:fixed;inset:0;z-index:80;display:flex;justify-content:center;align-items:stretch;padding:20px;background:rgba(5,9,15,.74);backdrop-filter:blur(10px)}
    .watchlist-manager-modal{width:min(1120px,100%);max-height:100%;display:flex;flex-direction:column;border-radius:28px;border:1px solid rgba(255,255,255,.08);background:linear-gradient(180deg,rgba(255,255,255,.02),transparent 30%),#0a0e16f5;box-shadow:0 24px 80px rgba(0,0,0,.35);overflow:hidden}
    .watchlist-manager-header{display:flex;justify-content:space-between;gap:16px;padding:22px 24px 16px;border-bottom:1px solid rgba(255,255,255,.08)}
    .watchlist-manager-header h2{margin:8px 0 0;font-size:clamp(1.7rem,2.6vw,2.4rem);line-height:1.05}
    .watchlist-manager-header p{margin:8px 0 0;color:var(--muted);line-height:1.55}
    .watchlist-manager-actions{display:flex;gap:10px;flex-wrap:wrap}
    .watchlist-manager-body{padding:18px 24px 24px;overflow:auto}
    .watchlist-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
    .watchlist-toolbar-group{display:flex;gap:10px;flex-wrap:wrap}
    .watchlist-toolbar button,.watchlist-row button,.watchlist-manager-close,.watchlist-save-button{border:1px solid rgba(255,255,255,.12);border-radius:999px;padding:10px 14px;background:rgba(255,255,255,.06);color:var(--text);font:inherit;cursor:pointer}
    .watchlist-save-button{border-color:rgba(75,208,138,.32);background:rgba(75,208,138,.14);color:#bdf0d0}
    .watchlist-manager-close{border-color:rgba(245,109,112,.24);background:rgba(245,109,112,.16)}
    .watchlist-toolbar button:hover,.watchlist-row button:hover,.watchlist-manager-close:hover,.watchlist-save-button:hover{transform:translateY(-1px)}
    .watchlist-status{margin-top:14px;padding:12px 14px;border-radius:16px;border:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.05);color:#d8cfb8;line-height:1.55}
    .watchlist-status.positive{border-color:rgba(75,208,138,.28);background:rgba(75,208,138,.14);color:#bdf0d0}
    .watchlist-status.negative{border-color:rgba(245,109,112,.28);background:rgba(245,109,112,.14);color:#ffd0ca}
    .watchlist-status.alert{border-color:rgba(245,183,58,.28);background:rgba(245,183,58,.12);color:#f5df9f}
    .watchlist-grid{margin-top:16px;display:grid;gap:10px}
    .watchlist-row{display:grid;grid-template-columns:52px minmax(140px,180px) minmax(220px,1fr) auto;gap:10px;align-items:center;padding:12px;border-radius:18px;border:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.04)}
    .watchlist-index{color:var(--muted);font-family:Trebuchet MS,sans-serif;text-align:center}
    .watchlist-row input{width:100%;padding:11px 12px;border-radius:14px;border:1px solid rgba(255,255,255,.12);background:rgba(8,12,20,.88);color:var(--text);font:inherit}
    .watchlist-row input:focus{outline:2px solid rgba(115,197,255,.35);outline-offset:1px}
    .watchlist-row-actions{display:flex;gap:8px;flex-wrap:wrap}
    .watchlist-row button.danger{border-color:rgba(245,109,112,.24);background:rgba(245,109,112,.14)}
    .watchlist-help{margin-top:14px;color:var(--muted);font-size:.88rem;line-height:1.55}
    @media (max-width:900px){.watchlist-row{grid-template-columns:1fr;}.watchlist-index{text-align:left}.watchlist-row-actions{justify-content:flex-start}}
  `;
  document.head.appendChild(style);
}

function parseWatchlistTs(source) {
  const pattern = /\{\s*code:\s*"([^"]+)"\s*,\s*name:\s*"([^"]+)"\s*\}/g;
  const entries = [];
  let match = null;
  while ((match = pattern.exec(source)) !== null) {
    entries.push({ code: match[1], name: match[2] });
  }
  return entries;
}

async function loadWatchlistEntries() {
  if (isTauriRuntime()) {
    return invokeTauri("get_watchlist_entries");
  }

  const candidates = [
    "./src/data/watchlist.ts",
    "../src/data/watchlist.ts",
    "/src/data/watchlist.ts"
  ];

  for (const candidate of candidates) {
    try {
      const response = await fetch(`${candidate}?ts=${Date.now()}`, { cache: "no-store" });
      if (!response.ok) continue;
      const text = await response.text();
      const parsed = parseWatchlistTs(text);
      if (parsed.length) return parsed;
    } catch (_error) {
      // try next candidate
    }
  }

  throw new Error("无法读取自选池");
}

function validateEntries(entries) {
  const seen = new Set();

  for (const entry of entries) {
    if (!/^\d{6}$/.test(entry.code)) {
      throw new Error(`股票代码格式不对：${entry.code || "空值"}`);
    }

    if (!entry.name.trim()) {
      throw new Error(`股票 ${entry.code} 缺少名称`);
    }

    if (seen.has(entry.code)) {
      throw new Error(`股票代码重复：${entry.code}`);
    }
    seen.add(entry.code);
  }

  if (!entries.length) {
    throw new Error("自选池至少保留 1 只股票");
  }
}

function buildModal() {
  const backdrop = document.createElement("div");
  backdrop.id = WATCHLIST_MANAGER_MODAL_ID;
  backdrop.className = "watchlist-manager-backdrop";
  backdrop.hidden = true;
  backdrop.innerHTML = `
    <div class="watchlist-manager-modal" role="dialog" aria-modal="true" aria-label="自选池管理">
      <div class="watchlist-manager-header">
        <div>
          <p class="section-label">Watchlist Manager</p>
          <h2>自选池管理</h2>
          <p>直接在桌面端里维护代码和名称。保存后会同步写回本地 <code>watchlist.ts</code>，并可自动触发后台刷新。</p>
        </div>
        <div class="watchlist-manager-actions">
          <button type="button" class="watchlist-save-button" data-action="save">保存并后台刷新</button>
          <button type="button" class="watchlist-manager-close" data-action="close">关闭</button>
        </div>
      </div>
      <div class="watchlist-manager-body">
        <div class="watchlist-toolbar">
          <div class="watchlist-toolbar-group">
            <button type="button" data-action="add">新增一行</button>
            <button type="button" data-action="reload">重新读取</button>
          </div>
          <div class="watchlist-toolbar-group">
            <span class="watchlist-help">可调整顺序，顺序会按你保存时的排列写回自选池。</span>
          </div>
        </div>
        <div class="watchlist-status" data-role="status">正在读取自选池…</div>
        <div class="watchlist-grid" data-role="grid"></div>
      </div>
    </div>
  `;
  document.body.appendChild(backdrop);

  backdrop.addEventListener("click", (event) => {
    if (event.target === backdrop) {
      closeModal();
    }
  });

  return backdrop;
}

function buildButton() {
  const button = document.createElement("button");
  button.id = WATCHLIST_MANAGER_BUTTON_ID;
  button.className = "watchlist-manager-button";
  button.type = "button";
  button.innerHTML = `<strong>自选池管理</strong><span>编辑代码和名称</span>`;
  button.addEventListener("click", openModal);
  document.body.appendChild(button);
  return button;
}

function getModal() {
  return document.getElementById(WATCHLIST_MANAGER_MODAL_ID) || buildModal();
}

function getStatusElement() {
  return getModal().querySelector('[data-role="status"]');
}

function getGridElement() {
  return getModal().querySelector('[data-role="grid"]');
}

function setStatus(message, tone = "") {
  const element = getStatusElement();
  element.className = `watchlist-status${tone ? ` ${tone}` : ""}`;
  element.textContent = message;
}

function createRow(entry, index) {
  const row = document.createElement("div");
  row.className = "watchlist-row";
  row.innerHTML = `
    <div class="watchlist-index">${index + 1}</div>
    <input data-field="code" maxlength="6" value="${entry.code}" placeholder="6位代码" />
    <input data-field="name" value="${entry.name}" placeholder="股票名称" />
    <div class="watchlist-row-actions">
      <button type="button" data-action="up">上移</button>
      <button type="button" data-action="down">下移</button>
      <button type="button" class="danger" data-action="remove">删除</button>
    </div>
  `;
  return row;
}

function readRows() {
  return Array.from(getGridElement().querySelectorAll(".watchlist-row")).map((row) => ({
    code: row.querySelector('[data-field="code"]').value.trim(),
    name: row.querySelector('[data-field="name"]').value.trim()
  }));
}

function renderRows(entries) {
  const grid = getGridElement();
  grid.innerHTML = "";
  entries.forEach((entry, index) => {
    grid.appendChild(createRow(entry, index));
  });
}

async function reloadWatchlist() {
  try {
    const entries = await loadWatchlistEntries();
    renderRows(entries);
    setStatus(isTauriRuntime() ? "已读取本地自选池，可直接修改后保存。" : "当前是浏览器模式，只支持查看，不支持直接写回本地文件。");
  } catch (error) {
    setStatus(`读取失败：${String(error)}`, "negative");
  }
}

function closeModal() {
  const modal = getModal();
  modal.hidden = true;
}

async function monitorSnapshotRefresh(previousSyncTime, expectedCount) {
  if (!isTauriRuntime()) return;

  window.clearInterval(watchlistMonitorTimer);
  let attempts = 0;
  watchlistMonitorTimer = window.setInterval(async () => {
    attempts += 1;
    try {
      const snapshot = await invokeTauri("get_dashboard_snapshot");
      if (
        snapshot &&
        snapshot.watchlistCount === expectedCount &&
        snapshot.syncTime &&
        snapshot.syncTime !== previousSyncTime
      ) {
        window.clearInterval(watchlistMonitorTimer);
        setStatus("后台刷新完成，页面即将自动更新。", "positive");
        window.setTimeout(() => window.location.reload(), 800);
        return;
      }
    } catch (_error) {
      // keep polling
    }

    if (attempts >= 24) {
      window.clearInterval(watchlistMonitorTimer);
      setStatus("已保存，但后台刷新还没结束。你可以稍后点击主界面的刷新按钮。", "alert");
    }
  }, 5000);
}

async function saveWatchlist() {
  if (!isTauriRuntime()) {
    setStatus("浏览器模式无法直接保存到本地文件，请在桌面版中使用。", "alert");
    return;
  }

  try {
    const entries = readRows();
    validateEntries(entries);

    const previousSnapshot = await invokeTauri("get_dashboard_snapshot").catch(() => null);
    const saved = await invokeTauri("save_watchlist_entries", { entries });
    setStatus(`已保存 ${saved.length} 只股票，正在后台刷新数据…`, "positive");

    const started = await invokeTauri("start_akshare_snapshot_refresh");
    if (started) {
      monitorSnapshotRefresh(previousSnapshot?.syncTime ?? "", saved.length);
    } else {
      setStatus("已保存自选池，但后台刷新已经在进行中。你可以稍后手动刷新主界面。", "alert");
    }
  } catch (error) {
    setStatus(`保存失败：${String(error)}`, "negative");
  }
}

function handleGridClick(event) {
  const button = event.target.closest("button");
  if (!button) return;
  const row = button.closest(".watchlist-row");
  if (!row) return;

  const grid = getGridElement();
  if (button.dataset.action === "remove") {
    row.remove();
  } else if (button.dataset.action === "up" && row.previousElementSibling) {
    grid.insertBefore(row, row.previousElementSibling);
  } else if (button.dataset.action === "down" && row.nextElementSibling) {
    grid.insertBefore(row.nextElementSibling, row);
  }

  renderRows(readRows());
}

async function openModal() {
  const modal = getModal();
  modal.hidden = false;
  await reloadWatchlist();
}

function ensureManagerUi() {
  ensureWatchlistManagerStyle();
  if (!document.getElementById(WATCHLIST_MANAGER_BUTTON_ID)) {
    buildButton();
  }

  const modal = getModal();
  modal.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;

    const action = button.dataset.action;
    if (action === "close") closeModal();
    if (action === "add") {
      const entries = readRows();
      entries.push({ code: "", name: "" });
      renderRows(entries);
      setStatus("已新增一行，填好代码和名称后再保存。");
    }
    if (action === "reload") reloadWatchlist();
    if (action === "save") saveWatchlist();
  });

  getGridElement().addEventListener("click", handleGridClick);

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !modal.hidden) {
      closeModal();
    }
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", ensureManagerUi, { once: true });
} else {
  ensureManagerUi();
}
