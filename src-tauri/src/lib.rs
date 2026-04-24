use std::{
    collections::HashSet,
    fs,
    path::{Path, PathBuf},
    process::Command,
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc,
    },
    thread,
};
use tauri::Emitter;

#[derive(Clone)]
struct RefreshState {
    running: Arc<AtomicBool>,
}

#[derive(Clone, serde::Serialize)]
struct RefreshFinishedPayload {
    status: String,
    message: String,
    sync_time: String,
}

#[derive(Clone, serde::Serialize, serde::Deserialize)]
struct WatchlistEntry {
    code: String,
    name: String,
}

fn looks_like_project_root(path: &Path) -> bool {
    path.join("src").join("data").join("akshare-snapshot.json").exists()
        && path.join("scripts").join("fetch_akshare_watchlist.py").exists()
}

fn find_project_root(start: &Path) -> Option<PathBuf> {
    for candidate in start.ancestors() {
        if looks_like_project_root(candidate) {
            return Some(candidate.to_path_buf());
        }
    }

    None
}

fn project_root() -> Result<PathBuf, String> {
    if let Ok(current_dir) = std::env::current_dir() {
        if let Some(root) = find_project_root(&current_dir) {
            return Ok(root);
        }
    }

    if let Ok(current_exe) = std::env::current_exe() {
        if let Some(exe_dir) = current_exe.parent() {
            if let Some(root) = find_project_root(exe_dir) {
                return Ok(root);
            }
        }
    }

    Err("无法定位项目根目录，未找到快照文件和同步脚本".to_string())
}

fn snapshot_path() -> Result<PathBuf, String> {
    Ok(project_root()?.join("src").join("data").join("akshare-snapshot.json"))
}

fn cycle_report_path() -> Result<PathBuf, String> {
    Ok(project_root()?
        .join("docs")
        .join("cycles")
        .join("watchlist-cycle-report.json"))
}

fn watchlist_path() -> Result<PathBuf, String> {
    Ok(project_root()?.join("src").join("data").join("watchlist.ts"))
}

fn watchlist_codes_path() -> Result<PathBuf, String> {
    Ok(project_root()?.join("watchlist_codes.txt"))
}

fn read_snapshot() -> Result<serde_json::Value, String> {
    let content = fs::read_to_string(snapshot_path()?).map_err(|error| error.to_string())?;
    serde_json::from_str::<serde_json::Value>(&content).map_err(|error| error.to_string())
}

fn read_cycle_report() -> Result<serde_json::Value, String> {
    let content = fs::read_to_string(cycle_report_path()?).map_err(|error| error.to_string())?;
    serde_json::from_str::<serde_json::Value>(&content).map_err(|error| error.to_string())
}

fn run_python_script(root: &Path, script_path: &str) -> Result<(), String> {
    let python = if cfg!(target_os = "windows") {
        "python"
    } else {
        "python3"
    };

    let output = Command::new(python)
        .arg(script_path)
        .current_dir(root)
        .output()
        .map_err(|error| format!("执行脚本失败：{error}"))?;

    if output.status.success() {
        return Ok(());
    }

    let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
    let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
    let details = if !stderr.is_empty() { stderr } else { stdout };
    Err(format!("{script_path} 执行失败：{details}"))
}

fn extract_watchlist_field(line: &str, key: &str) -> Option<String> {
    let marker = format!(r#"{key}: ""#);
    let start = line.find(&marker)? + marker.len();
    let tail = &line[start..];
    let end = tail.find('"')?;
    Some(tail[..end].trim().to_string())
}

fn parse_watchlist_entries(content: &str) -> Vec<WatchlistEntry> {
    content
        .lines()
        .filter_map(|line| {
            if !line.contains("code:") || !line.contains("name:") {
                return None;
            }

            let code = extract_watchlist_field(line, "code")?;
            let name = extract_watchlist_field(line, "name")?;
            Some(WatchlistEntry { code, name })
        })
        .collect()
}

fn normalize_watchlist_entries(entries: Vec<WatchlistEntry>) -> Result<Vec<WatchlistEntry>, String> {
    let mut normalized = Vec::new();
    let mut seen = HashSet::new();

    for entry in entries {
        let code = entry.code.trim().to_string();
        let name = entry.name.trim().to_string();

        if code.len() != 6 || !code.chars().all(|ch| ch.is_ascii_digit()) {
            return Err(format!("鑲＄エ浠ｇ爜鏍煎紡閿欒: {}", code));
        }

        if name.is_empty() {
            return Err(format!("鑲＄エ {} 鐨勫悕绉颁笉鑳戒负绌?:", code));
        }

        if !seen.insert(code.clone()) {
            return Err(format!("鑲＄エ浠ｇ爜閲嶅: {}", code));
        }

        normalized.push(WatchlistEntry { code, name });
    }

    if normalized.is_empty() {
        return Err("鑷€夋睜鑷冲皯淇濈暀 1 鍙偂绁?".to_string());
    }

    Ok(normalized)
}

fn render_watchlist_file(entries: &[WatchlistEntry]) -> String {
    let body = entries
        .iter()
        .map(|entry| format!(r#"  {{ code: "{}", name: "{}" }},"#, entry.code, entry.name))
        .collect::<Vec<_>>()
        .join("\n");

    format!(
        "export interface WatchlistSeed {{\n  code: string;\n  name: string;\n}}\n\nexport const watchlistSeeds: WatchlistSeed[] = [\n{body}\n];\n\nexport const watchlistCodes = watchlistSeeds.map((item) => item.code);\n"
    )
}

fn load_watchlist_entries() -> Result<Vec<WatchlistEntry>, String> {
    let content = fs::read_to_string(watchlist_path()?).map_err(|error| error.to_string())?;
    let entries = parse_watchlist_entries(&content);
    if entries.is_empty() {
        return Err("鏈В鏋愬埌鑷€夋睜鏁版嵁".to_string());
    }
    Ok(entries)
}

fn write_watchlist_entries(entries: &[WatchlistEntry]) -> Result<(), String> {
    fs::write(watchlist_path()?, render_watchlist_file(entries)).map_err(|error| error.to_string())?;

    let codes = entries
        .iter()
        .map(|entry| entry.code.as_str())
        .collect::<Vec<_>>()
        .join("\n");
    fs::write(watchlist_codes_path()?, format!("{codes}\n")).map_err(|error| error.to_string())?;
    Ok(())
}

#[tauri::command]
fn open_external_url(url: String) -> Result<(), String> {
    let trimmed = url.trim();
    if !(trimmed.starts_with("https://") || trimmed.starts_with("http://")) {
        return Err("仅允许打开 http 或 https 链接".to_string());
    }

    let mut command = if cfg!(target_os = "windows") {
        let mut cmd = Command::new("rundll32");
        cmd.arg("url.dll,FileProtocolHandler").arg(trimmed);
        cmd
    } else if cfg!(target_os = "macos") {
        let mut cmd = Command::new("open");
        cmd.arg(trimmed);
        cmd
    } else {
        let mut cmd = Command::new("xdg-open");
        cmd.arg(trimmed);
        cmd
    };

    command
        .spawn()
        .map(|_| ())
        .map_err(|error| format!("打开外部链接失败：{error}"))
}

#[tauri::command]
fn get_dashboard_snapshot() -> Result<serde_json::Value, String> {
    read_snapshot()
}

#[tauri::command]
fn get_watchlist_entries() -> Result<Vec<WatchlistEntry>, String> {
    load_watchlist_entries()
}

#[tauri::command]
fn save_watchlist_entries(entries: Vec<WatchlistEntry>) -> Result<Vec<WatchlistEntry>, String> {
    let normalized = normalize_watchlist_entries(entries)?;
    write_watchlist_entries(&normalized)?;
    Ok(normalized)
}

#[tauri::command]
fn get_cycle_report() -> Result<serde_json::Value, String> {
    read_cycle_report()
}

#[tauri::command]
fn refresh_akshare_snapshot(app: tauri::AppHandle) -> Result<serde_json::Value, String> {
    let root = project_root()?;
    run_python_script(&root, "scripts/fetch_akshare_watchlist.py")
        .map_err(|error| format!("行情同步失败：{error}"))?;
    run_python_script(&root, "scripts/generate_watchlist_cycle_report.py")
        .map_err(|error| format!("周期分析失败：{error}"))?;

    let _ = app.emit("akshare-sync-finished", "ok");
    read_snapshot()
}

#[tauri::command]
fn refresh_market_breadth_snapshot() -> Result<serde_json::Value, String> {
    let root = project_root()?;
    run_python_script(&root, "scripts/refresh_market_breadth_snapshot.py")
        .map_err(|error| format!("市场宽度刷新失败: {}", error))?;
    read_snapshot()
}

#[tauri::command]
fn start_akshare_snapshot_refresh(
    app: tauri::AppHandle,
    state: tauri::State<RefreshState>,
) -> Result<bool, String> {
    if state.running.swap(true, Ordering::SeqCst) {
        return Ok(false);
    }

    let app_handle = app.clone();
    let running = state.running.clone();

    thread::spawn(move || {
        let payload = match refresh_akshare_snapshot(app_handle.clone()) {
            Ok(snapshot) => {
                let sync_time = snapshot
                    .get("syncTime")
                    .and_then(|value| value.as_str())
                    .unwrap_or_default()
                    .to_string();

                RefreshFinishedPayload {
                    status: "success".to_string(),
                    message: if sync_time.is_empty() {
                        "行情快照已在后台刷新完成".to_string()
                    } else {
                        format!("行情快照已在后台刷新完成：{sync_time}")
                    },
                    sync_time,
                }
            }
            Err(error) => RefreshFinishedPayload {
                status: "error".to_string(),
                message: error,
                sync_time: String::new(),
            },
        };

        running.store(false, Ordering::SeqCst);
        let _ = app_handle.emit("akshare-refresh-status", payload);
    });

    Ok(true)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(RefreshState {
            running: Arc::new(AtomicBool::new(false)),
        })
        .invoke_handler(tauri::generate_handler![
            open_external_url,
            get_dashboard_snapshot,
            get_watchlist_entries,
            save_watchlist_entries,
            get_cycle_report,
            refresh_market_breadth_snapshot,
            refresh_akshare_snapshot,
            start_akshare_snapshot_refresh
        ])
        .run(tauri::generate_context!())
        .expect("运行 Tauri 应用失败");
}
