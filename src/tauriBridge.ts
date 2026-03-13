import { invoke } from "@tauri-apps/api/core";
import { getInitialSnapshot } from "./data/mock";
import type { DashboardSnapshot } from "./types";

export function isTauriRuntime() {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

export async function loadDashboardSnapshot(): Promise<DashboardSnapshot> {
  if (!isTauriRuntime()) {
    return getInitialSnapshot();
  }

  try {
    return await invoke<DashboardSnapshot>("get_dashboard_snapshot");
  } catch {
    return getInitialSnapshot();
  }
}

export async function refreshDashboardSnapshot(): Promise<DashboardSnapshot> {
  if (!isTauriRuntime()) {
    throw new Error("Refresh is available in the Tauri desktop app after Rust is installed.");
  }

  return invoke<DashboardSnapshot>("refresh_akshare_snapshot");
}
