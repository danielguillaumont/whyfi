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

type PingDetails = {
  target?: string | null;
  reachable?: boolean | null;
  packet_loss_percent?: number | null;
  min_latency_ms?: number | null;
  average_latency_ms?: number | null;
  max_latency_ms?: number | null;
  jitter_ms?: number | null;
};

type ConnectionDetails = {
  adapter_name?: string | null;
  adapter_type?: string | null;
  ipv4_address?: string | null;
  gateway?: string | null;
  is_up?: boolean | null;
  speed_mbps?: number | null;
  mtu?: number | null;
};

type InternetDetails = {
  reachable?: boolean | null;
  targets_tested?: number | null;
  targets_reachable?: number | null;
  probes?: PingDetails[] | null;
};

type DnsQueryDetails = {
  hostname?: string | null;
  resolver?: string | null;
  success?: boolean | null;
  latency_ms?: number | null;
};

type DnsDetails = {
  healthy?: boolean | null;
  default_resolver?: string | null;
  default_query?: DnsQueryDetails | null;
  likely_dns_issue?: boolean | null;
};

type WifiDetails = {
  connected?: boolean | null;
  interface_name?: string | null;
  signal_percent?: number | null;
  radio_type?: string | null;
  channel?: number | null;
  receive_rate_mbps?: number | null;
  transmit_rate_mbps?: number | null;
};

type LocalConfigDetails = {
  healthy?: boolean | null;
  active_adapters?: string[] | null;
  usable_ipv4_adapters?: string[] | null;
  link_local_ipv4_adapters?: string[] | null;
  likely_dhcp_issue?: boolean | null;
};

type DiagnosticDetails = {
  connection?: ConnectionDetails | null;
  gateway?: PingDetails | null;
  internet?: InternetDetails | null;
  dns?: DnsDetails | null;
  wifi?: WifiDetails | null;
  local_config?: LocalConfigDetails | null;
  completed?: boolean | null;
  error?: string | null;
};

type ProgressEvent = {
  type: "progress";
  message: string;
};

type ResultEvent = {
  type: "result";
  diagnosis: Diagnosis;
  details: DiagnosticDetails;
};

type DiagnosticEvent = ProgressEvent | ResultEvent;

type DetailRowProps = {
  label: string;
  value: string | number | null | undefined;
};

const DEV_PREVIEW_DIAGNOSES: Diagnosis[] = [
  {
    code: "no_connection",
    title: "No active network connection.",
    confidence: 98,
    summary:
      "WHYFI could not find an active physical network connection on this computer.",
    evidence: [
      "No active Wi-Fi or Ethernet connection was detected.",
      "No usable IPv4 connection was available.",
      "The network investigation could not continue upstream.",
    ],
    recommendation:
      "Connect to Wi-Fi or Ethernet, then run WHYFI again.",
  },
  {
    code: "local_config_issue",
    title: "Your device has a network configuration problem.",
    confidence: 94,
    summary:
      "Your computer is connected to a network adapter, but its local IP configuration does not look usable.",
    evidence: [
      "The active adapter does not have a normal usable IPv4 configuration.",
      "A DHCP or automatic addressing problem may have occurred.",
      "The issue appears before traffic reaches your router.",
    ],
    recommendation:
      "Reconnect the adapter or renew its network configuration, then diagnose again.",
  },
  {
    code: "gateway_issue",
    title: "Your router is not responding.",
    confidence: 93,
    summary:
      "Your computer appears connected, but WHYFI cannot reliably reach the local gateway.",
    evidence: [
      "The active network adapter is available.",
      "A default gateway was discovered.",
      "Gateway reachability checks failed or showed severe packet loss.",
    ],
    recommendation:
      "Check your router connection and Wi-Fi link. Restarting or reconnecting to the router may help.",
  },
  {
    code: "internet_issue",
    title: "Your local network works, but the internet does not.",
    confidence: 92,
    summary:
      "Your computer can reach the router, but multiple independent internet targets are not responding.",
    evidence: [
      "Your local gateway is reachable.",
      "Local network communication appears healthy.",
      "Multiple public internet targets could not be reached.",
    ],
    recommendation:
      "Check your modem or ISP connection. The problem is likely beyond your local device.",
  },
  {
    code: "dns_issue",
    title: "DNS looks like the problem.",
    confidence: 91,
    summary:
      "Your internet connection appears reachable, but your configured DNS resolver is not resolving names correctly.",
    evidence: [
      "Direct internet connectivity is working.",
      "The configured DNS resolver failed its lookup.",
      "An alternate public resolver successfully answered the same request.",
    ],
    recommendation:
      "Try reconnecting to the network or switching to a working DNS resolver.",
  },
  {
    code: "wifi_issue",
    title: "Your Wi-Fi connection looks unstable.",
    confidence: 89,
    summary:
      "WHYFI found evidence that the wireless link between your computer and router is degrading the connection.",
    evidence: [
      "Wi-Fi signal quality is weak.",
      "Packet loss was observed between this computer and the local gateway.",
      "The evidence points to the local wireless connection rather than the ISP.",
    ],
    recommendation:
      "Move closer to the router, reduce interference, or try another Wi-Fi band or access point.",
  },
  {
    code: "unstable_connection",
    title: "Your connection is unstable.",
    confidence: 87,
    summary:
      "The connection is working, but WHYFI detected instability across multiple measurements.",
    evidence: [
      "Repeated network samples showed inconsistent response times.",
      "Packet loss or elevated jitter was detected.",
      "The instability was reproduced across more than one measurement.",
    ],
    recommendation:
      "Run another diagnosis after a few minutes and compare the results. Persistent instability may require router or ISP troubleshooting.",
  },
  {
    code: "unknown",
    title: "WHYFI could not isolate one clear cause.",
    confidence: 48,
    summary:
      "Some measurements look unusual, but the available evidence is not strong enough to blame one part of the connection.",
    evidence: [
      "The connection produced mixed diagnostic signals.",
      "No single failure condition had enough supporting evidence.",
      "WHYFI avoided making a low-confidence diagnosis.",
    ],
    recommendation:
      "Run the diagnosis again or use the technical details to inspect the measurements more closely.",
  },
];

function DetailRow({ label, value }: DetailRowProps) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  return (
    <div className="evidence-item">
      <strong>{label}:</strong>
      <span>{value}</span>
    </div>
  );
}

function yesNo(value: boolean | null | undefined) {
  if (value === null || value === undefined) {
    return undefined;
  }

  return value ? "Yes" : "No";
}

function metric(
  value: number | null | undefined,
  suffix: string
) {
  if (value === null || value === undefined) {
    return undefined;
  }

  return `${value} ${suffix}`;
}

function App() {
  const [appState, setAppState] = useState<AppState>("ready");
  const [diagnosis, setDiagnosis] = useState<Diagnosis | null>(null);
  const [details, setDetails] = useState<DiagnosticDetails | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);
  const [isPreview, setIsPreview] = useState(false);
  const [progressMessage, setProgressMessage] = useState(
    "Preparing diagnostic engine..."
  );

  async function handleDiagnose() {
    setAppState("diagnosing");
    setDiagnosis(null);
    setDetails(null);
    setErrorMessage("");
    setShowTechnicalDetails(false);
    setIsPreview(false);
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
      setDetails(result.details);
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

  function previewDiagnosis(preview: Diagnosis) {
    setDiagnosis({
      ...preview,
      evidence: [...preview.evidence],
    });
    setDetails(null);
    setErrorMessage("");
    setShowTechnicalDetails(false);
    setIsPreview(true);
    setAppState("result");
  }

  function returnToReady() {
    setAppState("ready");
    setDiagnosis(null);
    setDetails(null);
    setErrorMessage("");
    setShowTechnicalDetails(false);
    setIsPreview(false);
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

            {import.meta.env.DEV && (
              <section
                className="check-card"
                style={{
                  marginTop: "12px",
                  minHeight: "auto",
                }}
              >
                <span className="check-number">DEV</span>

                <h2>Preview problem states</h2>

                <p>
                  Development only. These buttons preview result screens
                  without changing your real network.
                </p>

                <div
                  className="result-actions"
                  style={{
                    flexWrap: "wrap",
                    marginTop: "18px",
                  }}
                >
                  {DEV_PREVIEW_DIAGNOSES.map((preview) => (
                    <button
                      className="secondary-button"
                      style={{ marginTop: 0 }}
                      type="button"
                      key={preview.code}
                      onClick={() => previewDiagnosis(preview)}
                    >
                      {preview.code}
                    </button>
                  ))}
                </div>
              </section>
            )}
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
                {import.meta.env.DEV && isPreview
                  ? "Development preview"
                  : "Diagnosis complete"}
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
                onClick={returnToReady}
              >
                Back
              </button>

              {details && (
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() =>
                    setShowTechnicalDetails(
                      (currentValue) => !currentValue
                    )
                  }
                >
                  {showTechnicalDetails
                    ? "Hide technical details"
                    : "Technical details"}
                </button>
              )}
            </div>

            {showTechnicalDetails && details && (
              <>
                <div className="result-grid">
                  {details.connection && (
                    <article className="result-panel">
                      <p className="result-panel-label">Connection</p>

                      <div className="evidence-list">
                        <DetailRow
                          label="Adapter"
                          value={details.connection.adapter_name}
                        />
                        <DetailRow
                          label="Type"
                          value={details.connection.adapter_type}
                        />
                        <DetailRow
                          label="IPv4"
                          value={details.connection.ipv4_address}
                        />
                        <DetailRow
                          label="Gateway"
                          value={details.connection.gateway}
                        />
                        <DetailRow
                          label="Link up"
                          value={yesNo(details.connection.is_up)}
                        />
                        <DetailRow
                          label="Link speed"
                          value={metric(
                            details.connection.speed_mbps,
                            "Mbps"
                          )}
                        />
                        <DetailRow
                          label="MTU"
                          value={details.connection.mtu}
                        />
                      </div>
                    </article>
                  )}

                  {details.gateway && (
                    <article className="result-panel">
                      <p className="result-panel-label">Gateway</p>

                      <div className="evidence-list">
                        <DetailRow
                          label="Reachable"
                          value={yesNo(details.gateway.reachable)}
                        />
                        <DetailRow
                          label="Average latency"
                          value={metric(
                            details.gateway.average_latency_ms,
                            "ms"
                          )}
                        />
                        <DetailRow
                          label="Packet loss"
                          value={metric(
                            details.gateway.packet_loss_percent,
                            "%"
                          )}
                        />
                        <DetailRow
                          label="Jitter"
                          value={metric(
                            details.gateway.jitter_ms,
                            "ms"
                          )}
                        />
                      </div>
                    </article>
                  )}
                </div>

                <div className="result-grid">
                  {details.internet && (
                    <article className="result-panel">
                      <p className="result-panel-label">Internet</p>

                      <div className="evidence-list">
                        <DetailRow
                          label="Reachable"
                          value={yesNo(details.internet.reachable)}
                        />
                        <DetailRow
                          label="Targets reachable"
                          value={
                            details.internet.targets_reachable !== undefined &&
                            details.internet.targets_tested !== undefined
                              ? `${details.internet.targets_reachable}/${details.internet.targets_tested}`
                              : undefined
                          }
                        />

                        {details.internet.probes?.map((probe) => (
                          <div
                            className="evidence-item"
                            key={probe.target ?? "probe"}
                          >
                            <strong>{probe.target ?? "Target"}:</strong>

                            <span>
                              {metric(
                                probe.average_latency_ms,
                                "ms avg"
                              ) ?? "No latency"}
                              {" / "}
                              {metric(
                                probe.packet_loss_percent,
                                "% loss"
                              ) ?? "No loss data"}
                            </span>
                          </div>
                        ))}
                      </div>
                    </article>
                  )}

                  {details.dns && (
                    <article className="result-panel">
                      <p className="result-panel-label">DNS</p>

                      <div className="evidence-list">
                        <DetailRow
                          label="Healthy"
                          value={yesNo(details.dns.healthy)}
                        />
                        <DetailRow
                          label="Resolver"
                          value={details.dns.default_resolver}
                        />
                        <DetailRow
                          label="Query latency"
                          value={metric(
                            details.dns.default_query?.latency_ms,
                            "ms"
                          )}
                        />
                        <DetailRow
                          label="DNS issue detected"
                          value={yesNo(
                            details.dns.likely_dns_issue
                          )}
                        />
                      </div>
                    </article>
                  )}
                </div>

                <div className="result-grid">
                  {details.wifi && (
                    <article className="result-panel">
                      <p className="result-panel-label">Wi-Fi</p>

                      <div className="evidence-list">
                        <DetailRow
                          label="Connected"
                          value={yesNo(details.wifi.connected)}
                        />
                        <DetailRow
                          label="Signal"
                          value={metric(
                            details.wifi.signal_percent,
                            "%"
                          )}
                        />
                        <DetailRow
                          label="Radio"
                          value={details.wifi.radio_type}
                        />
                        <DetailRow
                          label="Channel"
                          value={details.wifi.channel}
                        />
                        <DetailRow
                          label="Receive rate"
                          value={metric(
                            details.wifi.receive_rate_mbps,
                            "Mbps"
                          )}
                        />
                        <DetailRow
                          label="Transmit rate"
                          value={metric(
                            details.wifi.transmit_rate_mbps,
                            "Mbps"
                          )}
                        />
                      </div>
                    </article>
                  )}

                  {details.local_config && (
                    <article className="result-panel">
                      <p className="result-panel-label">
                        Local configuration
                      </p>

                      <div className="evidence-list">
                        <DetailRow
                          label="Healthy"
                          value={yesNo(
                            details.local_config.healthy
                          )}
                        />
                        <DetailRow
                          label="DHCP issue"
                          value={yesNo(
                            details.local_config.likely_dhcp_issue
                          )}
                        />
                        <DetailRow
                          label="Active adapters"
                          value={
                            details.local_config.active_adapters?.join(
                              ", "
                            )
                          }
                        />
                        <DetailRow
                          label="Usable IPv4 adapters"
                          value={
                            details.local_config.usable_ipv4_adapters?.join(
                              ", "
                            )
                          }
                        />
                      </div>
                    </article>
                  )}
                </div>
              </>
            )}
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
                onClick={returnToReady}
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
