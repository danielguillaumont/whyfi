mod sidecar_protocol;

use sidecar_protocol::{SidecarProtocol, StderrCapture};
use tauri::Emitter;
use tauri_plugin_shell::process::CommandEvent;
use tauri_plugin_shell::ShellExt;

async fn run_diagnosis_sidecar(app: tauri::AppHandle) -> Result<String, String> {
    let sidecar_command = app
        .shell()
        .sidecar("whyfi-engine")
        .map_err(|error| format!("Could not locate the WHYFI diagnostic engine: {error}"))?
        .args(["--stream-json"])
        .set_raw_out(true);

    let (mut receiver, _child) = sidecar_command
        .spawn()
        .map_err(|error| format!("Could not start the WHYFI diagnostic engine: {error}"))?;

    let mut protocol = SidecarProtocol::default();
    let mut protocol_error = None;
    let mut stderr = StderrCapture::default();
    let mut termination = None;

    while let Some(event) = receiver.recv().await {
        match event {
            CommandEvent::Stdout(bytes) if protocol_error.is_none() => {
                // Continue draining both pipes on a protocol error until the sidecar exits.
                protocol_error = protocol
                    .push(&bytes, |line| {
                        app.emit("whyfi-diagnostic-event", line).map_err(|error| {
                            format!("Could not send diagnostic progress to the interface: {error}")
                        })
                    })
                    .err();
            }
            CommandEvent::Stderr(bytes) => stderr.push(&bytes),

            CommandEvent::Error(error) => {
                return Err(format!("WHYFI diagnostic engine process error: {error}"));
            }

            CommandEvent::Terminated(payload) => {
                termination = Some(payload.code);
            }

            _ => {}
        }
    }

    if let Some(error) = protocol_error {
        return Err(error);
    }

    let exit_code = termination
        .ok_or_else(|| "WHYFI diagnostic engine ended without a termination status.".to_string())?;
    protocol.finish(exit_code, &stderr)
}

#[tauri::command]
async fn run_diagnosis(app: tauri::AppHandle) -> Result<String, String> {
    run_diagnosis_sidecar(app).await
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![run_diagnosis])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
