import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import "./App.css";

type AppState = "ready" | "diagnosing" | "result" | "error";

type Diagnosis = {
  code: string;
  title: string;
  confidence: number;
  summary: string;
  evidence: string[];
  recommendation: string;
};

type ProgressEvent = {
  type: "progress";
  message: string;
};

type ResultEvent = {
  type: "result";
  diagnosis: Diagnosis;
  details: unknown;
};

type DiagnosticEvent = ProgressEvent | ResultEvent;

function App() {
  const [appState, setAppState] = useState<AppState>("ready");
  const [diagnosis, setDiagnosis] = useState<Diagnosis | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [progressMessage, setProgressMessage] = useState(
    "Preparing diagnostic engine..."
  );

  async function handleDiagnose() {
    setAppState("diagnosing");
    setDiagnosis(null);
    setErrorMessage("");
    setProgressMessage("Preparing diagnostic engine...");

    let unlisten: UnlistenFn | null = null;

    try {
      unlisten = await listen<string>(
        "whyfi-diagnostic-event",
        (event) => {
          try {
            const diagnosticEvent = JSON.parse(
              event.payload
            ) as DiagnosticEvent;

            if (diagnosticEvent.type === "progress") {
              setProgressMessage(diagnosticEvent.message);
            }
          } catch (error) {
            console.error(
              "Could not parse WHYFI diagnostic event:",
              error
            );
          }
        }
      );

      const response = await invoke<string>("run_diagnosis");
      const result = JSON.parse(response) as DiagnosticEvent;

      if (result.type !== "result") {
        throw new Error(
          "WHYFI did not return a final diagnostic result."
        );
      }

      setDiagnosis(result.diagnosis);
      setAppState("result");
    } catch (error) {
      console.error("WHYFI diagnosis failed:", error);

      setErrorMessage(
        error instanceof Error ? error.message : String(error)
      );

      setAppState("error");
    } finally {
      if (unlisten) {
        unlisten();
      }
    }
  }

  function getResultTone(code: string) {
    if (code === "healthy") {
      return "healthy";
    }

    if (code === "unknown") {
      return "neutral";
    }

    return "problem";
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

        {appState === "ready" && (
          <>
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
              >
                <span className="diagnose-button-icon">+</span>
                Diagnose
              </button>
            </section>

            <section
              className="check-grid"
              aria-label="WHYFI diagnostic areas"
            >
              <article className="check-card">
                <span className="check-number">01</span>
                <h2>Your device</h2>
                <p>
                  Adapter, IP address, DHCP, and local configuration.
                </p>
              </article>

              <article className="check-card">
                <span className="check-number">02</span>
                <h2>Your network</h2>
                <p>
                  Wi-Fi signal, gateway reachability, loss, and jitter.
                </p>
              </article>

              <article className="check-card">
                <span className="check-number">03</span>
                <h2>The internet</h2>
                <p>
                  Public connectivity, DNS, and upstream stability.
                </p>
              </article>
            </section>
          </>
        )}

        {appState === "diagnosing" && (
          <section className="diagnosing-view">
            <div className="diagnostic-spinner" aria-hidden="true">
              <span />
              <span />
              <span />
            </div>

            <p className="eyebrow">DIAGNOSIS IN PROGRESS</p>

            <h1>Investigating your connection.</h1>

            <p className="diagnosing-copy">
              WHYFI is collecting evidence from your device, local network,
              router, DNS, and internet connection.
            </p>

            <div className="scan-line">
              <span className="scan-pulse" />
              {progressMessage}
            </div>

            <p className="diagnosing-note">
              Everything stays on this computer.
            </p>
          </section>
        )}

        {appState === "result" && diagnosis && (
          <section
            className={`result-view result-${getResultTone(
              diagnosis.code
            )}`}
          >
            <div className="result-topline">
              <div className="result-status">
                <span className="result-status-dot" />
                Diagnosis complete
              </div>

              <span className="confidence-badge">
                {diagnosis.confidence}% confidence
              </span>
            </div>

            <p className="eyebrow">WHYFI RESULT</p>

            <h1>{diagnosis.title}</h1>

            <p className="result-summary">{diagnosis.summary}</p>

            <div className="result-grid">
              <article className="result-panel evidence-panel">
                <p className="result-panel-label">Evidence</p>

                <div className="evidence-list">
                  {diagnosis.evidence.map((item, index) => (
                    <div className="evidence-item" key={`${item}-${index}`}>
                      <span className="evidence-check">
                        {"\u2713"}
                      </span>
                      <span>{item}</span>
                    </div>
                  ))}
                </div>
              </article>

              <article className="result-panel recommendation-panel">
                <p className="result-panel-label">What to do</p>
                <p>{diagnosis.recommendation}</p>
              </article>
            </div>

            <div className="result-actions">
              <button
                className="diagnose-button"
                type="button"
                onClick={handleDiagnose}
              >
                <span className="diagnose-button-icon">
                  {"\u21bb"}
                </span>
                Diagnose again
              </button>

              <button
                className="secondary-button"
                type="button"
                onClick={() => setAppState("ready")}
              >
                Back
              </button>
            </div>
          </section>
        )}

        {appState === "error" && (
          <section className="error-view">
            <div className="error-symbol">!</div>

            <p className="eyebrow">DIAGNOSIS INTERRUPTED</p>

            <h1>WHYFI couldn't finish the investigation.</h1>

            <p className="error-copy">
              The diagnostic engine returned an error before a result could
              be produced.
            </p>

            <div className="error-message">{errorMessage}</div>

            <div className="result-actions">
              <button
                className="diagnose-button"
                type="button"
                onClick={handleDiagnose}
              >
                Try again
              </button>

              <button
                className="secondary-button"
                type="button"
                onClick={() => setAppState("ready")}
              >
                Back
              </button>
            </div>
          </section>
        )}

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
