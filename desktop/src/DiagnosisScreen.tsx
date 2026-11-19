import { DEV_PREVIEW_DIAGNOSES } from "./diagnosisPreviews";
import type { Diagnosis } from "./diagnosticTypes";
import type { WorkspaceState } from "./workspaceState";

function InvestigationStatus({ state, cancel }: {
  state: Extract<WorkspaceState, { phase: "running" }>;
  cancel: () => void;
}) {
  return (
    <section className="workspace-view diagnosis-view">
      <div className="view-heading diagnosis-heading">
        <h1 tabIndex={-1}>Investigating connection</h1>
        <button className="button button-secondary diagnosis-cancel" type="button"
          disabled={!state.canCancel && !state.cancelling}
          aria-disabled={state.cancelling || undefined}
          onClick={() => { if (state.canCancel) cancel(); }}>
          Cancel
        </button>
      </div>
      <div className="investigation-status">
        <span className="activity-icon" aria-hidden="true"><span className="working-indicator" /></span>
        <div className="activity-copy">
          <h2>Current activity</h2>
          <p role="status">{state.progress}</p>
        </div>
      </div>
    </section>
  );
}

export function DiagnosisScreen({ state, start, cancel, preview }: {
  state: WorkspaceState;
  start: () => void;
  cancel: () => void;
  preview: (diagnosis: Diagnosis) => void;
}) {
  if (state.phase === "running") return <InvestigationStatus state={state} cancel={cancel} />;

  const retry = state.phase === "failed" || state.phase === "timed_out";
  const title = state.phase === "timed_out" ? "Investigation timed out"
    : state.phase === "failed" ? "Investigation could not finish"
    : state.phase === "cancelled" ? "Investigation cancelled" : "Diagnose connection";
  const cleanupNotice = state.phase === "cancelled"
    ? state.message.replace(/^Investigation cancelled\.(?:\s+|$)/, "") : "";

  return (
    <section className="workspace-view diagnosis-view">
      <div className="diagnosis-intro">
        <h1 tabIndex={-1}>{title}</h1>
        <p className="view-description">
          {retry ? "Try the diagnosis again to collect a fresh set of measurements."
            : "Find out whether the problem is with your device, local network, or internet connection."}
        </p>
      </div>
      {cleanupNotice && (
        <div className="notice diagnosis-notice">
          <span className="notice-icon" aria-hidden="true">i</span>
          <span>{cleanupNotice}</span>
        </div>
      )}
      <div className="workspace-actions">
        <button className="button button-primary diagnosis-start" type="button" onClick={start}>
          {retry ? "Try again" : "Start diagnosis"}
        </button>
      </div>
      {retry && (
        <details className="result-panel recovery-details" open={state.phase === "timed_out"}>
          <summary>Investigation details</summary>
          <p>{state.message}</p>
        </details>
      )}
      {!retry && (
        <section className="result-panel check-panel">
          <h2>What WHYFI checks</h2>
          <dl>
            <div><dt>Device</dt><dd>Network adapter and IP settings</dd></div>
            <div><dt>Local network</dt><dd>Wi-Fi signal and whether your router responds</dd></div>
            <div><dt>Internet and DNS</dt><dd>Whether public IPs respond and names resolve</dd></div>
          </dl>
        </section>
      )}
      {import.meta.env.DEV && !retry && (
        <details className="result-panel recovery-details">
          <summary>Development result previews</summary>
          <div className="workspace-actions">
            {DEV_PREVIEW_DIAGNOSES.map((sample) => (
              <button className="button button-secondary" type="button"
                key={sample.code} onClick={() => preview(sample)}>{sample.code}</button>
            ))}
          </div>
        </details>
      )}
    </section>
  );
}
