import { DEV_PREVIEW_DIAGNOSES } from "./diagnosisPreviews";
import type { Diagnosis } from "./diagnosticTypes";
import type { WorkspaceState } from "./workspaceState";

const checkAreas = [
  { title: "Device", explanation: "Adapter and IP configuration" },
  { title: "Local network", explanation: "Wi-Fi and gateway response" },
  { title: "Internet", explanation: "Public target reachability" },
  { title: "DNS", explanation: "Windows and resolver lookups" },
] as const;

function ChecklineCoverage() {
  return (
    <section className="checkline-coverage" aria-labelledby="checkline-coverage-title">
      <div className="checkline-coverage-heading">
        <h2 id="checkline-coverage-title">What gets checked</h2>
        <p>Four areas · Not measured yet</p>
      </div>
      <ol className="checkline-rail" aria-label="Areas of network investigation">
        {checkAreas.map(({ title, explanation }) => (
          <li key={title}>
            <span className="checkline-rail-node" aria-hidden="true" />
            <h3>{title}</h3>
            <p>{explanation}</p>
            <span className="checkline-untested">Not checked</span>
          </li>
        ))}
      </ol>
    </section>
  );
}

function InvestigationStatus({ state, cancel }: {
  state: Extract<WorkspaceState, { phase: "running" }>;
  cancel: () => void;
}) {
  return (
    <section className="workspace-view diagnosis-view checkline-diagnose checkline-running">
      <div className="checkline-intro">
        <span className="checkline-pill"><span className="checkline-pill-dot" aria-hidden="true" /> Check in progress</span>
        <h1 tabIndex={-1}>Checking your connection.</h1>
        <p className="view-description">Gathering connection measurements. WHYFI will report what the available evidence actually supports.</p>
      </div>
      <section className="checkline-run-activity" aria-label="Investigation activity">
        <span className="checkline-run-indicator" aria-hidden="true"><span className="working-indicator" /></span>
        <div className="checkline-run-copy">
          <h2>Current activity</h2>
          <p role="status">{state.progress}</p>
        </div>
        <button className="button button-secondary diagnosis-cancel" type="button"
          disabled={!state.canCancel && !state.cancelling}
          aria-disabled={state.cancelling || undefined}
          onClick={() => { if (state.canCancel) cancel(); }}>
          Cancel
        </button>
      </section>
      <p className="checkline-run-footnote">Results stay on this device. The network tests generate DNS and ICMP traffic.</p>
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
    : state.phase === "cancelled" ? "Investigation cancelled" : "Find out what's not working.";
  const cleanupNotice = state.phase === "cancelled"
    ? state.message.replace(/^Investigation cancelled\.(?:\s+|$)/, "") : "";
  const description = retry
    ? "The previous check didn't finish. Try again to collect a fresh set of measurements."
    : state.phase === "cancelled"
      ? "No conclusion was recorded. You can start another check whenever you're ready."
      : "WHYFI checks your device, local network, public reachability, and DNS. You get a clear answer when the evidence supports one.";

  return (
    <section className="workspace-view diagnosis-view checkline-diagnose">
      <div className="checkline-intro">
        {retry && <span className="checkline-pill checkline-pill-attention">Check incomplete</span>}
        {state.phase === "cancelled" && <span className="checkline-pill checkline-pill-neutral">Stopped</span>}
        <h1 tabIndex={-1}>{title}</h1>
        <p className="view-description">{description}</p>
        {cleanupNotice && (
          <div className="notice diagnosis-notice">
            <span className="notice-icon" aria-hidden="true">i</span>
            <span>{cleanupNotice}</span>
          </div>
        )}
        <div className="checkline-cta-area">
          <button className="button button-primary diagnosis-start" type="button" onClick={start}>
            {retry ? "Try again" : state.phase === "cancelled" ? "Start diagnosis" : "Check my connection"}
            <span className="checkline-cta-mark" aria-hidden="true">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none">
                <path d="M3 17h6l6-10h6" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
                <circle cx="3" cy="17" r="2" fill="currentColor" />
                <circle cx="21" cy="7" r="2" fill="currentColor" />
              </svg>
            </span>
          </button>
          <p className="checkline-cta-note">No account. No automatic report upload.</p>
        </div>
        {retry && (
          <details className="result-panel recovery-details checkline-recovery" open={state.phase === "timed_out"}>
            <summary>Investigation details</summary>
            <p>{state.message}</p>
          </details>
        )}
      </div>

      {!retry && <ChecklineCoverage />}
      <div className="checkline-help">
        <strong>One check. A clearer next step.</strong>
        <span>Results stay on this device. Tests generate network probes.</span>
      </div>

      {import.meta.env.DEV && !retry && (
        <details className="checkline-dev-previews">
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
