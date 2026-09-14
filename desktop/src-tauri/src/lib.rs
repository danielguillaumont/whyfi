use std::path::PathBuf;
use std::process::Command;

#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;

#[tauri::command]
fn run_diagnosis() -> Result<String, String> {
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));

    let repo_root = manifest_dir
        .parent()
        .and_then(|path| path.parent())
        .ok_or_else(|| "Could not locate the WHYFI project root.".to_string())?
        .to_path_buf();

    let python_path = repo_root
        .join(".venv")
        .join("Scripts")
        .join("python.exe");

    if !python_path.exists() {
        return Err(format!(
            "WHYFI Python environment was not found at {}.",
            python_path.display()
        ));
    }

    let mut command = Command::new(&python_path);

    command
        .args(["-m", "whyfi", "--json"])
        .current_dir(&repo_root);

    #[cfg(target_os = "windows")]
    command.creation_flags(0x08000000);

    let output = command
        .output()
        .map_err(|error| format!("Could not start the WHYFI diagnostic engine: {error}"))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr)
            .trim()
            .to_string();

        if stderr.is_empty() {
            return Err(format!(
                "WHYFI diagnostic engine exited with status {}.",
                output.status
            ));
        }

        return Err(format!(
            "WHYFI diagnostic engine failed: {stderr}"
        ));
    }

    let stdout = String::from_utf8(output.stdout)
        .map_err(|error| format!("WHYFI returned invalid output: {error}"))?;

    let result = stdout.trim().to_string();

    if result.is_empty() {
        return Err("WHYFI diagnostic engine returned no data.".to_string());
    }

    Ok(result)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![run_diagnosis])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
