import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import "./App.css";

type Diagnosis = {
  code: string;
  title: string;
  confidence: number;
  summary: string;
  evidence: string[];
  recommendation: string;
};

type WhyfiResult = {
  diagnosis: Diagnosis;
  details: unknown;
};

function App() {
  const [statusMessage, setStatusMessage] = useState(
    "Ready when you are."
  );
  const [isDiagnosing, setIsDiagnosing] = useState(false);
  const [diagnosis, setDiagnosis] = useState<Diagnosis | null>(null);

  async function handleDiagnose() {
    setIsDiagnosing(true);
    setDiagnosis(null);
    setStatusMessage("Investigating your network...");

    try {
      const response = await invoke<string>("run_diagnosis");
      const result: WhyfiResult = JSON.parse(response);

      setDiagnosis(result.diagnosis);
      setStatusMessage(
        `${result.diagnosis.title} Confidence: ${result.diagnosis.confidence}%`
      );
    } catch (error) {
      console.error("WHYFI diagnosis failed:", error);

      setStatusMessage(
        `Diagnosis failed: ${
          error instanceof Error ? error.message : String(error)
        }`
      );
    } finally {
      setIsDiagnosing(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="whyfi-card">
        <header className="brand">
          <div className="brand-mark">W</div>

          <div>
            <p className="brand-name">WHYFI</p>
            <p className="brand-tagline">
              Network diagnosis without the jargon.
            </p>
          </div>
        </header>

        <div className="status-pill">
          <span className="status-dot" />
          Local-first network diagnostics
        </div>

        <section className="hero">
          <p className="eyebrow">ONE CLICK. REAL EVIDENCE.</p>

          <h1>What's wrong with my internet?</h1>

          <p className="hero-copy">
            WHYFI checks your computer, Wi-Fi, router, internet connection,
            and DNS to find where the problem actually starts.
          </p>

          <button
            className="diagnose-button"
            type="button"
            onClick={handleDiagnose}
            disabled={isDiagnosing}
          >
            <span className="diagnose-button-icon">
              {isDiagnosing ? "..." : "+"}
            </span>

            {isDiagnosing ? "Diagnosing..." : "Diagnose"}
          </button>

          <p className="status-message">{statusMessage}</p>

          {diagnosis && (
            <section className="diagnosis-preview">
              <h2>{diagnosis.title}</h2>

              <p>
                <strong>Confidence:</strong> {diagnosis.confidence}%
              </p>

              <p>{diagnosis.summary}</p>

              <p>
                <strong>Recommendation:</strong>{" "}
                {diagnosis.recommendation}
              </p>
            </section>
          )}
        </section>

        <section className="check-grid" aria-label="WHYFI diagnostic areas">
          <article className="check-card">
            <span className="check-number">01</span>
            <h2>Your device</h2>
            <p>Adapter, IP address, DHCP, and local configuration.</p>
          </article>

          <article className="check-card">
            <span className="check-number">02</span>
            <h2>Your network</h2>
            <p>Wi-Fi signal, gateway reachability, loss, and jitter.</p>
          </article>

          <article className="check-card">
            <span className="check-number">03</span>
            <h2>The internet</h2>
            <p>Public connectivity, DNS, and upstream stability.</p>
          </article>
        </section>

        <footer className="app-footer">
          <span>No login.</span>
          <span>No cloud dashboard.</span>
          <span>Evidence first.</span>
        </footer>
      </section>
    </main>
  );
}

export default App;
