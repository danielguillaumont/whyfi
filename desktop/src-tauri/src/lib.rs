mod investigation;
mod process;
mod sidecar_protocol;

use investigation::{investigate, investigation_timeout, InvestigationResult, Investigations};
use serde::Serialize;
use tauri::{ipc::Channel, State};
use tauri_plugin_shell::ShellExt;
use tokio::time::Instant;

fn launch_sidecar(app: tauri::AppHandle) -> Result<process::Sidecar, String> {
    let sidecar_command = app
        .shell()
        .sidecar("whyfi-engine")
        .map_err(|error| format!("Could not locate the WHYFI diagnostic engine: {error}"))?
        .args(["--stream-json"]);

    process::Sidecar::spawn(sidecar_command.into())
        .map_err(|error| format!("Could not start the WHYFI diagnostic engine: {error}"))
}

#[derive(Serialize)]
#[serde(
    tag = "type",
    rename_all = "snake_case",
    rename_all_fields = "camelCase"
)]
enum InvestigationEvent {
    Started { run_id: String },
    Progress { run_id: String, message: String },
}

#[tauri::command]
async fn start_diagnosis(
    app: tauri::AppHandle,
    investigations: State<'_, Investigations>,
    events: Channel<InvestigationEvent>,
) -> Result<InvestigationResult, String> {
    let run = investigations.start()?;
    let deadline = Instant::now() + investigation_timeout();
    let run_id = run.id.clone();
    events
        .send(InvestigationEvent::Started {
            run_id: run_id.clone(),
        })
        .map_err(|error| format!("Could not send investigation acknowledgement: {error}"))?;

    // The worker owns the slot and child even if the webview disconnects.
    tauri::async_runtime::spawn(async move {
        investigate(
            run,
            move || launch_sidecar(app),
            deadline,
            |message| {
                events
                    .send(InvestigationEvent::Progress {
                        run_id: run_id.clone(),
                        message: message.into(),
                    })
                    .map_err(|error| {
                        format!("Could not send diagnostic progress to the interface: {error}")
                    })
            },
        )
        .await
    })
    .await
    .map_err(|error| format!("Investigation worker failed: {error}"))
}

#[tauri::command]
fn cancel_diagnosis(run_id: String, investigations: State<'_, Investigations>) -> bool {
    investigations.cancel(&run_id)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(Investigations::default())
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![start_diagnosis, cancel_diagnosis])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
