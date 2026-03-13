use serde::{Deserialize, Serialize};
use std::{fs, path::PathBuf, process::Command};
use tauri::Emitter;

#[derive(Serialize, Deserialize, Clone)]
struct WatchSignal {
    label: String,
    value: String,
    level: String,
}

#[derive(Serialize, Deserialize, Clone)]
struct WatchSnapshot {
    symbol: String,
    name: String,
    market: String,
    sector: String,
    price: f64,
    #[serde(rename = "changePct")]
    change_pct: f64,
    momentum: u8,
    #[serde(rename = "volumeRatio")]
    volume_ratio: f64,
    note: String,
    thesis: String,
    sparkline: Vec<f64>,
    signals: Vec<WatchSignal>,
}

#[derive(Serialize, Deserialize, Clone)]
struct DashboardSnapshot {
    #[serde(rename = "syncTime")]
    sync_time: String,
    #[serde(rename = "watchlistCount")]
    watchlist_count: usize,
    #[serde(rename = "strongSignals")]
    strong_signals: usize,
    #[serde(rename = "avgChange")]
    avg_change: f64,
    mood: String,
    stocks: Vec<WatchSnapshot>,
}

fn project_root() -> Result<PathBuf, String> {
    std::env::current_dir().map_err(|error| error.to_string())
}

fn snapshot_path() -> Result<PathBuf, String> {
    Ok(project_root()?.join("src").join("data").join("akshare-snapshot.json"))
}

fn read_snapshot() -> Result<DashboardSnapshot, String> {
    let content = fs::read_to_string(snapshot_path()?).map_err(|error| error.to_string())?;
    serde_json::from_str::<DashboardSnapshot>(&content).map_err(|error| error.to_string())
}

#[tauri::command]
fn get_dashboard_snapshot() -> Result<DashboardSnapshot, String> {
    read_snapshot()
}

#[tauri::command]
fn refresh_akshare_snapshot(app: tauri::AppHandle) -> Result<DashboardSnapshot, String> {
    let root = project_root()?;
    let python = if cfg!(target_os = "windows") { "python" } else { "python3" };

    let output = Command::new(python)
        .arg("scripts/fetch_akshare_watchlist.py")
        .current_dir(&root)
        .output()
        .map_err(|error| format!("failed to run sync script: {error}"))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
        let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
        let details = if !stderr.is_empty() { stderr } else { stdout };
        return Err(format!("AkShare sync failed: {details}"));
    }

    let _ = app.emit("akshare-sync-finished", "ok");
    read_snapshot()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            get_dashboard_snapshot,
            refresh_akshare_snapshot
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
