use std::io::{BufRead, BufReader, Read};
use std::path::PathBuf;
use std::process::{Command, Stdio};

#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;

use tauri::Emitter;

fn run_diagnosis_process(app: tauri::AppHandle) -> Result<String, String> {
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
        .args(["-m", "whyfi", "--stream-json"])
        .current_dir(&repo_root)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());

    #[cfg(target_os = "windows")]
    command.creation_flags(0x08000000);

    let mut child = command
        .spawn()
        .map_err(|error| {
            format!(
                "Could not start the WHYFI diagnostic engine: {error}"
            )
        })?;

    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| {
            "Could not read WHYFI diagnostic output.".to_string()
        })?;

    let reader = BufReader::new(stdout);
    let mut final_event: Option<String> = None;

    for line in reader.lines() {
        let line = line.map_err(|error| {
            format!(
                "Could not read WHYFI diagnostic output: {error}"
            )
        })?;

        let event = line.trim();

        if event.is_empty() {
            continue;
        }

        app.emit(
            "whyfi-diagnostic-event",
            event.to_string(),
        )
        .map_err(|error| {
            format!(
                "Could not send diagnostic progress to the interface: {error}"
            )
        })?;

        final_event = Some(event.to_string());
    }

    let status = child
        .wait()
        .map_err(|error| {
            format!(
                "Could not wait for the WHYFI diagnostic engine: {error}"
            )
        })?;

    let mut stderr = String::new();

    if let Some(mut error_output) = child.stderr.take() {
        error_output
            .read_to_string(&mut stderr)
            .map_err(|error| {
                format!(
                    "Could not read WHYFI diagnostic errors: {error}"
                )
            })?;
    }

    if !status.success() {
        let stderr = stderr.trim();

        if stderr.is_empty() {
            return Err(format!(
                "WHYFI diagnostic engine exited with status {status}."
            ));
        }

        return Err(format!(
            "WHYFI diagnostic engine failed: {stderr}"
        ));
    }

    let result = final_event.ok_or_else(|| {
        "WHYFI diagnostic engine returned no data.".to_string()
    })?;

    if !result.contains("\"type\":\"result\"") {
        return Err(
            "WHYFI diagnostic engine did not return a final result."
                .to_string(),
        );
    }

    Ok(result)
}

#[tauri::command]
async fn run_diagnosis(
    app: tauri::AppHandle,
) -> Result<String, String> {
    tauri::async_runtime::spawn_blocking(move || {
        run_diagnosis_process(app)
    })
    .await
    .map_err(|error| {
        format!(
            "WHYFI diagnostic task could not complete: {error}"
        )
    })?
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(
            tauri::generate_handler![run_diagnosis]
        )
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
