import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import { applyCycleAnalysis, getEmbeddedCycleReport } from "./data/cycle";
import { getInitialSnapshot, normalizeDashboardSnapshot } from "./data/mock";
import type { DashboardSnapshot } from "./types";

export interface DashboardRefreshEvent {
  status: "success" | "error";
  message: string;
  syncTime: string;
}

export function isTauriRuntime() {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

function isValidDashboardSnapshot(value: unknown): value is DashboardSnapshot {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Partial<DashboardSnapshot>;
  if (!Array.isArray(candidate.stocks)) {
    return false;
  }

  return candidate.stocks.every((stock) => (
    stock &&
    typeof stock === "object" &&
    Array.isArray(stock.sparkline) &&
    Array.isArray((stock as { candles?: unknown[] }).candles) &&
    Array.isArray(stock.signals) &&
    !!stock.metadata &&
    typeof stock.metadata === "object" &&
    typeof stock.metadata.officialWebsite === "string" &&
    typeof stock.metadata.websiteSource === "string" &&
    !!stock.technicals &&
    typeof stock.technicals === "object" &&
    !!stock.technicals.macd &&
    typeof stock.technicals.macd === "object" &&
    typeof stock.technicals.macd.signalLabel === "string" &&
    !!stock.technicals.rsi14 &&
    typeof stock.technicals.rsi14 === "object" &&
    typeof stock.technicals.rsi14.signalLabel === "string" &&
    !!stock.selectionScore &&
    typeof stock.selectionScore === "object" &&
    typeof stock.selectionScore.total === "number" &&
    Array.isArray(stock.selectionScore.factors) &&
    !!stock.priceDistribution &&
    Array.isArray(stock.priceDistribution.bands) &&
    !!stock.amplitudeDistribution &&
    Array.isArray(stock.amplitudeDistribution.bands)
  ));
}

export async function loadDashboardSnapshot(): Promise<DashboardSnapshot> {
  if (!isTauriRuntime()) {
    return getInitialSnapshot();
  }

  try {
    const snapshot = await invoke<unknown>("get_dashboard_snapshot");
    if (!isValidDashboardSnapshot(snapshot)) {
      return getInitialSnapshot();
    }

    const cycleReport = await loadCycleReport();
    return applyCycleAnalysis(normalizeDashboardSnapshot(snapshot), cycleReport);
  } catch {
    return getInitialSnapshot();
  }
}

export async function startDashboardRefresh(): Promise<boolean> {
  if (!isTauriRuntime()) {
    throw new Error("安装 Rust 并在 Tauri 桌面端运行后，才能执行刷新。");
  }

  return invoke<boolean>("start_akshare_snapshot_refresh");
}

export async function listenDashboardRefresh(
  onRefresh: (event: DashboardRefreshEvent) => void
): Promise<UnlistenFn> {
  if (!isTauriRuntime()) {
    return () => {};
  }

  return listen<{
    status?: string;
    message?: string;
    sync_time?: string;
  }>("akshare-refresh-status", (event) => {
    const payload = event.payload || {};
    onRefresh({
      status: payload.status === "error" ? "error" : "success",
      message: payload.message || "",
      syncTime: payload.sync_time || ""
    });
  });
}

export interface WatchlistEntry {
  code: string;
  name: string;
}

export async function getWatchlistEntries(): Promise<WatchlistEntry[]> {
  if (!isTauriRuntime()) {
    throw new Error("仅 Tauri 桌面端支持此操作。");
  }
  return invoke<WatchlistEntry[]>("get_watchlist_entries");
}

export async function saveWatchlistEntries(entries: WatchlistEntry[]): Promise<WatchlistEntry[]> {
  if (!isTauriRuntime()) {
    throw new Error("仅 Tauri 桌面端支持此操作。");
  }
  return invoke<WatchlistEntry[]>("save_watchlist_entries", { entries });
}

export async function openExternalLink(url: string): Promise<void> {
  if (!url) {
    return;
  }

  if (!isTauriRuntime()) {
    window.open(url, "_blank", "noopener,noreferrer");
    return;
  }

  await invoke("open_external_url", { url });
}

async function loadCycleReport(): Promise<unknown> {
  if (!isTauriRuntime()) {
    return getEmbeddedCycleReport();
  }

  try {
    return await invoke<unknown>("get_cycle_report");
  } catch {
    return getEmbeddedCycleReport();
  }
}
