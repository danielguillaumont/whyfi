import type { Diagnosis, DiagnosticDetails } from "./diagnosticTypes";
import { resultSummary } from "./resultSummary";
import "./ResultOverview.css";

type SummaryCheck = ReturnType<typeof resultSummary>["dns"];

const checkAreas = ["Device", "Local network", "Internet", "DNS"] as const;

function ResultCheck({ area, check }: { area: string; check: SummaryCheck }) {
  return (
    <li className={`checkline-result-check checkline-result-check-${check.state}`}>
      <span className="checkline-result-node" aria-hidden="true" />
      <h3>{area}</h3>
      {area !== check.label && <p className="checkline-result-check-source">{check.label}</p>}
      <p className="checkline-result-check-status">{check.status}</p>
      {check.measurements.length > 0 && (
        <ul className="checkline-result-measurements">
          {check.measurements.map((measurement) => <li key={measurement}>{measurement}</li>)}
        </ul>
      )}
    </li>
  );
}

export function ResultOverview({ diagnosis, details, start, showEvidence }: {
  diagnosis: Diagnosis;
  details: DiagnosticDetails | null;
  start: () => void;
  showEvidence: () => void;
}) {
  const summary = resultSummary(diagnosis, details);
  const checks = [...summary.path, summary.dns];

  return (
    <section className={`workspace-view result-overview checkline-result checkline-result-${summary.tone}`}>
      <header className="checkline-result-header">
        <div className="checkline-result-intro">
          <div className="checkline-result-meta">
            <span id="diagnosis-outcome" className={`result-status result-status-${summary.tone}`}>
              <span aria-hidden="true">{summary.tone === "healthy" ? "✓" : summary.tone === "problem" ? "!" : "?"}</span>
              {summary.status}
            </span>
            {details === null && <span className="checkline-preview-label">Development preview · No measured evidence{summary.confidence !== undefined ? ` · Rule-based engine score ${summary.confidence}` : ""}</span>}
          </div>
          <h1 tabIndex={-1} aria-describedby="diagnosis-outcome">{diagnosis.title}</h1>
          <p className="view-description">{diagnosis.summary}</p>
        </div>
        {details !== null && (
          <button className="button button-secondary checkline-evidence-entry" type="button"
            onClick={showEvidence} data-evidence-entry>
            View evidence
          </button>
        )}
      </header>

      {details !== null && (
        <section className="checkline-result-observations" aria-labelledby="result-path-heading">
          <div className="checkline-result-section-heading">
            <h2 id="result-path-heading">What WHYFI observed</h2>
            <span>Four investigation areas</span>
          </div>
          <ol className="checkline-result-path" role="list" aria-label="Results by investigation area">
            {checks.map((check, i) => (
              <ResultCheck key={checkAreas[i]} area={checkAreas[i]} check={check} />
            ))}
          </ol>
          {summary.confidence !== undefined && (
            <p className="checkline-result-score">
              Rule-based engine score <strong>{summary.confidence}</strong>
              <span>Not a probability of correctness</span>
            </p>
          )}
        </section>
      )}

      <div className={`checkline-result-bottom ${summary.findings.length === 0 ? "checkline-result-bottom-solo" : ""}`}>
        {summary.findings.length > 0 && (
          <section className="checkline-result-findings" aria-labelledby="checkline-findings-heading">
            <h2 id="checkline-findings-heading">Supporting findings</h2>
            <ul className="checkline-result-finding-list">
              {summary.findings.map((finding) => <li key={finding}>{finding}</li>)}
            </ul>
          </section>
        )}
        <section className="checkline-result-next" aria-labelledby="result-next-heading">
          <h2 id="result-next-heading">{diagnosis.recommendation ? "Your next step" : "Investigation actions"}</h2>
          {diagnosis.recommendation && <p>{diagnosis.recommendation}</p>}
          <button className="button button-primary checkline-repeat" type="button" onClick={start}>
            Run another check
          </button>
        </section>
      </div>
    </section>
  );
}
