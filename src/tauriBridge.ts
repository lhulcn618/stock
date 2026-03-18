import { invoke } from "@tauri-apps/api/core";
import { applyCycleAnalysis, getEmbeddedCycleReport } from "./data/cycle";
import { getInitialSnapshot } from "./data/mock";
import type { DashboardSnapshot } from "./types";

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
    return applyCycleAnalysis(snapshot, cycleReport);
  } catch {
    return getInitialSnapshot();
  }
}

export async function refreshDashboardSnapshot(): Promise<DashboardSnapshot> {
  if (!isTauriRuntime()) {
    throw new Error("安装 Rust 并在 Tauri 桌面端运行后，才能执行刷新。");
  }

  const snapshot = await invoke<unknown>("refresh_akshare_snapshot");
  if (!isValidDashboardSnapshot(snapshot)) {
    throw new Error("桌面端返回的快照结构不完整，已拒绝使用该结果。");
  }

  const cycleReport = await loadCycleReport();
  return applyCycleAnalysis(snapshot, cycleReport);
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
