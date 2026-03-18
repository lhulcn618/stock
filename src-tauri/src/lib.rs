use std::{
    fs,
    path::{Path, PathBuf},
    process::Command,
};
use tauri::Emitter;

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

fn read_snapshot() -> Result<serde_json::Value, String> {
    let content = fs::read_to_string(snapshot_path()?).map_err(|error| error.to_string())?;
    serde_json::from_str::<serde_json::Value>(&content).map_err(|error| error.to_string())
}

fn read_cycle_report() -> Result<serde_json::Value, String> {
    let content = fs::read_to_string(cycle_report_path()?).map_err(|error| error.to_string())?;
    serde_json::from_str::<serde_json::Value>(&content).map_err(|error| error.to_string())
}

fn run_python_script(root: &Path, script_path: &str) -> Result<(), String> {
    let python = if cfg!(target_os = "windows") { "python" } else { "python3" };
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
fn get_cycle_report() -> Result<serde_json::Value, String> {
    read_cycle_report()
}

#[tauri::command]
fn refresh_akshare_snapshot(app: tauri::AppHandle) -> Result<serde_json::Value, String> {
    let root = project_root()?;
    run_python_script(&root, "scripts/fetch_akshare_watchlist.py")
        .map_err(|error| format!("AkShare 同步失败：{error}"))?;
    run_python_script(&root, "scripts/generate_watchlist_cycle_report.py")
        .map_err(|error| format!("周期分析失败：{error}"))?;

    let _ = app.emit("akshare-sync-finished", "ok");
    read_snapshot()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            open_external_url,
            get_dashboard_snapshot,
            get_cycle_report,
            refresh_akshare_snapshot
        ])
        .run(tauri::generate_context!())
        .expect("运行 Tauri 应用失败");
}
