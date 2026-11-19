import type { Diagnosis, DiagnosticDetails } from "./diagnosticTypes";
import { resultSummary } from "./resultSummary";
import "./ResultOverview.css";

function CheckSummary({ check }: { check: ReturnType<typeof resultSummary>["dns"] }) {
  return (
    <>
      <h3>{check.label}</h3>
      <p className={`check-status check-status-${check.state}`}>{check.status}</p>
      {check.measurements.length > 0 && (
        <ul className="check-measurements">
          {check.measurements.map(measurement => <li key={measurement}>{measurement}</li>)}
        </ul>
      )}
    </>
  );
}

export function ResultOverview({ diagnosis, details, start, showEvidence }: {
  diagnosis: Diagnosis;
  details: DiagnosticDetails | null;
  start: () => void;
  showEvidence: () => void;
}) {
  const summary = resultSummary(diagnosis, details);

  return (
    <section className="workspace-view result-overview">
      <header className="result-hero">
        <div className="result-meta">
          <span id="diagnosis-outcome" className={`result-status result-status-${summary.tone}`}>
            <span aria-hidden="true">{summary.tone === "healthy" ? "✓" : summary.tone === "problem" ? "!" : "?"}</span>
            {summary.status}
          </span>
          {details === null && <span>Development preview</span>}
          {summary.confidence !== undefined && <span>Rule-based engine score {summary.confidence}</span>}
        </div>
        <h1 tabIndex={-1} aria-describedby="diagnosis-outcome">{diagnosis.title}</h1>
        <p className="view-description">{diagnosis.summary}</p>
      </header>

      <section className="result-panel result-next" aria-labelledby="result-next-heading">
        <div>
          <h2 id="result-next-heading">{diagnosis.recommendation ? "Next action" : "Investigation actions"}</h2>
          {diagnosis.recommendation && <p>{diagnosis.recommendation}</p>}
        </div>
        <div className="workspace-actions">
          <button className="button button-primary" type="button" onClick={start}>Run again</button>
          {details !== null && (
            <button className="button button-secondary" type="button" onClick={showEvidence} data-evidence-entry>
              View evidence
            </button>
          )}
        </div>
      </section>

      {details !== null && <section className="result-panel result-path" aria-labelledby="result-path-heading">
        <h2 id="result-path-heading">Connection checks</h2>
        <ol className="connection-checks" role="list">
          {summary.path.map(item => (
            <li key={item.label}><CheckSummary check={item} /></li>
          ))}
        </ol>
        <div className="result-dns">
          <CheckSummary check={summary.dns} />
        </div>
      </section>}

      {summary.findings.length > 0 && (
        <section className="result-panel">
          <h2>Supporting findings</h2>
          <ul className="findings">
            {summary.findings.map(item => <li key={item}>{item}</li>)}
          </ul>
        </section>
      )}
    </section>
  );
}
