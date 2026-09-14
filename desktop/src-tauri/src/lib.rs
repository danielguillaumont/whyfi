use tauri::Emitter;
use tauri_plugin_shell::process::CommandEvent;
use tauri_plugin_shell::ShellExt;

async fn run_diagnosis_sidecar(
    app: tauri::AppHandle,
) -> Result<String, String> {
    let sidecar_command = app
        .shell()
        .sidecar("whyfi-engine")
        .map_err(|error| {
            format!(
                "Could not locate the WHYFI diagnostic engine: {error}"
            )
        })?
        .args(["--stream-json"]);

    let (mut receiver, _child) = sidecar_command
        .spawn()
        .map_err(|error| {
            format!(
                "Could not start the WHYFI diagnostic engine: {error}"
            )
        })?;

    let mut final_event: Option<String> = None;
    let mut stderr_lines: Vec<String> = Vec::new();
    let mut exit_code: Option<i32> = None;
    let mut terminated = false;

    while let Some(event) = receiver.recv().await {
        match event {
            CommandEvent::Stdout(bytes) => {
                let line = String::from_utf8_lossy(&bytes)
                    .trim()
                    .to_string();

                if line.is_empty() {
                    continue;
                }

                app.emit(
                    "whyfi-diagnostic-event",
                    line.clone(),
                )
                .map_err(|error| {
                    format!(
                        "Could not send diagnostic progress to the interface: {error}"
                    )
                })?;

                if line.contains("\"type\":\"result\"") {
                    final_event = Some(line);
                }
            }

            CommandEvent::Stderr(bytes) => {
                let line = String::from_utf8_lossy(&bytes)
                    .trim()
                    .to_string();

                if !line.is_empty() {
                    stderr_lines.push(line);
                }
            }

            CommandEvent::Error(error) => {
                return Err(format!(
                    "WHYFI diagnostic engine process error: {error}"
                ));
            }

            CommandEvent::Terminated(payload) => {
                terminated = true;
                exit_code = payload.code;
            }

            _ => {}
        }
    }

    if !terminated {
        return Err(
            "WHYFI diagnostic engine ended without a termination status."
                .to_string(),
        );
    }

    if exit_code != Some(0) {
        let stderr = stderr_lines.join("\n");

        if stderr.is_empty() {
            return Err(format!(
                "WHYFI diagnostic engine exited with code {:?}.",
                exit_code
            ));
        }

        return Err(format!(
            "WHYFI diagnostic engine failed: {stderr}"
        ));
    }

    let result = final_event.ok_or_else(|| {
        "WHYFI diagnostic engine did not return a final result."
            .to_string()
    })?;

    Ok(result)
}

#[tauri::command]
async fn run_diagnosis(
    app: tauri::AppHandle,
) -> Result<String, String> {
    run_diagnosis_sidecar(app).await
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(
            tauri::generate_handler![run_diagnosis]
        )
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
