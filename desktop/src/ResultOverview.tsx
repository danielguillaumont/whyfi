import type { Diagnosis } from "./diagnosticTypes";

export function ResultOverview({ diagnosis, hasEvidence, start, showEvidence }: {
  diagnosis: Diagnosis;
  hasEvidence: boolean;
  start: () => void;
  showEvidence: () => void;
}) {
  const status = diagnosis.code === "healthy" ? "healthy"
    : diagnosis.code === "unknown" ? "inconclusive" : "problem";
  const labels = { healthy: "Healthy", inconclusive: "Inconclusive", problem: "Problem found" };

  return (
    <section className="workspace-view">
      <div className="result-meta">
        {!hasEvidence && <span>Development preview</span>}
        <span className={`result-status result-status-${status}`}>
          <span aria-hidden="true">{status === "healthy" ? "✓" : status === "problem" ? "!" : "?"}</span>
          {labels[status]}
        </span>
        {diagnosis.confidence != null && <span>{diagnosis.confidence}% confidence</span>}
      </div>
      <h1 tabIndex={-1}>{diagnosis.title}</h1>
      <p className="view-description">{diagnosis.summary}</p>
      {diagnosis.recommendation && (
        <article className="result-panel">
          <h2>What to do</h2>
          <p>{diagnosis.recommendation}</p>
        </article>
      )}
      <div className="workspace-actions">
        <button className="button button-primary" type="button" onClick={start}>Run again</button>
        {hasEvidence && (
          <button className="button button-secondary" type="button" onClick={showEvidence} data-evidence-entry>
            View evidence
          </button>
        )}
      </div>
      {diagnosis.evidence.length > 0 && (
        <article className="result-panel">
          <h2>Evidence</h2>
          <ul className="findings">
            {diagnosis.evidence.map((item, index) => <li key={index}>{item}</li>)}
          </ul>
        </article>
      )}
    </section>
  );
}
