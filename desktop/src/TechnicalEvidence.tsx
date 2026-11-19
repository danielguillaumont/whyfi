import type { DiagnosticDetails } from "./diagnosticTypes";
import { resolverEvidenceRows, systemDnsSummary } from "./dnsEvidence";
import { collectionNotes } from "./collectionNotes";

type DetailRowProps = {
  label: string;
  value: string | number | null | undefined;
};

function DetailRow({ label, value }: DetailRowProps) {
  if (
    !((typeof value === "string" && value.length > 0) ||
      (typeof value === "number" && Number.isFinite(value)))
  ) {
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
  if (typeof value !== "boolean") {
    return undefined;
  }

  return value ? "Yes" : "No";
}

function metric(
  value: number | null | undefined,
  suffix: string
) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return undefined;
  }

  return `${value} ${suffix}`;
}

function detailRecords<T extends object>(items: T[] | null | undefined): T[] {
  return Array.isArray(items)
    ? items.filter((item) => typeof item === "object" && item !== null && !Array.isArray(item))
    : [];
}

function adapterList(items: string[] | null | undefined) {
  return Array.isArray(items)
    ? items.filter((item) => typeof item === "string").join(", ")
    : undefined;
}

export function TechnicalEvidence({ details, findings, onBack }: {
  details: DiagnosticDetails;
  findings: string[];
  onBack: () => void;
}) {
  const { rows: notes, fallback: collectionError } = collectionNotes(details.collection_errors, details.error);
  const engineFindings = Array.isArray(findings)
    ? findings.filter(item => typeof item === "string" && item.trim().length > 0)
    : [];
  return (
    <section className="workspace-view">
      <div className="view-heading">
        <h1 tabIndex={-1}>Technical evidence</h1>
        <button className="button button-secondary" type="button" onClick={onBack}>Back to result</button>
      </div>
      <p className="view-description">Measurements from the current investigation.</p>
      {engineFindings.length > 0 && (
        <section className="result-panel">
          <h2>Diagnosis findings</h2>
          <ul className="findings">
            {engineFindings.map((item, index) => <li key={index}>{item}</li>)}
          </ul>
        </section>
      )}
      <div className="result-grid">
        {details.connection && (
          <article className="result-panel">
            <h2 className="result-panel-label">Connection</h2>

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
            <h2 className="result-panel-label">Gateway</h2>

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
            <h2 className="result-panel-label">Internet</h2>

            <div className="evidence-list">
              <DetailRow
                label="Reachable"
                value={yesNo(details.internet.reachable)}
              />
              <DetailRow
                label="Targets reachable"
                value={
                  typeof details.internet.targets_reachable === "number" &&
                  typeof details.internet.targets_tested === "number" &&
                  details.internet.targets_tested > 0
                    ? `${details.internet.targets_reachable}/${details.internet.targets_tested}`
                    : undefined
                }
              />

              {detailRecords(details.internet.probes).map((probe, index) => (
                <div
                  className="evidence-item"
                  key={typeof probe.target === "string" ? probe.target : index}
                >
                  <strong>{typeof probe.target === "string" ? probe.target : "Target"}:</strong>

                  <span>
                    {metric(
                      probe.average_latency_ms,
                      "ms avg"
                    ) ?? "Latency unavailable"}
                    {" / "}
                    {metric(
                      probe.packet_loss_percent,
                      "% loss"
                    ) ?? "Loss unavailable"}
                  </span>
                </div>
              ))}
            </div>
          </article>
        )}

        {details.dns && (
          <article className="result-panel">
            <h2 className="result-panel-label">DNS</h2>

            <div className="evidence-list">
              <DetailRow
                label="Direct resolver test resolved"
                value={yesNo(details.dns.healthy) ?? "Unavailable"}
              />
              <DetailRow
                label="First configured resolver"
                value={details.dns.default_resolver}
              />
              <DetailRow
                label="First resolver latency"
                value={metric(
                  details.dns.default_query?.latency_ms,
                  "ms"
                )}
              />
              <DetailRow label="Details" value={details.dns.error} />
              {details.dns.system_query && (
                <DetailRow label="Windows DNS client" value={systemDnsSummary(details.dns.system_query)} />
              )}
              <DetailRow label="Attribution" value={details.dns.attribution_error} />
              {detailRecords(details.dns.configured_queries).map((query, index) => (
                <DetailRow
                  key={typeof query.resolver === "string" ? query.resolver : index}
                  label={typeof query.resolver === "string" ? query.resolver : "Configured resolver"}
                  value={
                    query.success === true
                      ? metric(query.latency_ms, "ms") ?? "Resolved"
                      : [
                          query.success === false ? "Lookup failed" : "Unavailable",
                          typeof query.error === "string" ? query.error : undefined,
                        ].filter(Boolean).join(" — ")
                  }
                />
              ))}
              {resolverEvidenceRows(details.dns.resolver_evidence).map((row, index) => (
                <DetailRow key={`${row.label}-${index}`} label={row.label} value={row.value} />
              ))}
            </div>
          </article>
        )}
      </div>

      <div className="result-grid">
        {details.wifi && (
          <article className="result-panel">
            <h2 className="result-panel-label">Wi-Fi</h2>

            <div className="evidence-list">
              <DetailRow
                label="Connected"
                value={yesNo(details.wifi.connected) ?? "Unavailable"}
              />
              <DetailRow label="Interface" value={details.wifi.interface_name} />
              <DetailRow label="Details" value={details.wifi.error} />
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
            <h2 className="result-panel-label">
              Local configuration
            </h2>

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
                value={adapterList(details.local_config.active_adapters)}
              />
              <DetailRow
                label="Usable IPv4 adapters"
                value={adapterList(details.local_config.usable_ipv4_adapters)}
              />
            </div>
          </article>
        )}
      </div>
      {(notes.length > 0 || collectionError) && (
        <article className="result-panel">
          <h2 className="result-panel-label">Collection notes</h2>
          {notes.length ? (
            <div className="evidence-list">
              {notes.map(({ label, value }, index) => (
                <DetailRow key={index} label={label} value={value} />
              ))}
            </div>
          ) : <p>{collectionError}</p>}
        </article>
      )}
    </section>
  );
}
