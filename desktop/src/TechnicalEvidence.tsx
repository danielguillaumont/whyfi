import type { ReactNode } from "react";
import type { DiagnosticDetails } from "./diagnosticTypes";
import { evidenceDetails, evidenceSections } from "./evidenceDetails";
import "./TechnicalEvidence.css";

type Evidence = ReturnType<typeof evidenceDetails>;
type SectionKey = typeof evidenceSections[number][0];

function Rows({ rows }: { rows: Evidence["device"][number]["rows"] }) {
  return <dl className="technical-rows">
    {rows.map(({ label, value, technical }, index) => (
      <div key={index} className={value === "Unavailable" || value === "Not assessed" ? "technical-row-unavailable" : undefined}>
        <dt>{label}</dt>
        <dd>{technical && value !== "Unavailable" ? <code>{value}</code> : value}</dd>
      </div>
    ))}
  </dl>;
}

function MeasurementGroup({ group, technicalTitle = false }: {
  group: Evidence["device"][number]; technicalTitle?: boolean;
}) {
  return <div className="technical-group">
    <h3>{technicalTitle ? <code>{group.title}</code> : group.title}</h3>
    {group.note ? <p className="technical-muted">{group.note}</p> : <Rows rows={group.rows} />}
  </div>;
}

function SectionNotes({ notes, heading }: { notes: Evidence["notes"]["device"]; heading: "h2" | "h3" }) {
  if (!notes.length) return null;
  const Heading = heading;
  return <div className="technical-group technical-notes">
    <Heading>Collection notes</Heading>
    <Rows rows={notes} />
  </div>;
}

function EvidenceSection({ id, label, notes, children }: {
  id: SectionKey; label: string; notes: Evidence["notes"]["device"]; children: ReactNode;
}) {
  return <section className="technical-section" aria-labelledby={`evidence-${id}`}>
    <h2 id={`evidence-${id}`} tabIndex={-1}>{label}</h2>
    {children}
    <SectionNotes notes={notes} heading="h3" />
  </section>;
}

const probeColumns = [
  ["status", "Reachability"], ["average", "Avg. latency"], ["loss", "Packet loss"],
  ["sent", "Packets sent"], ["received", "Packets received"],
] as const;

function InternetMeasurements({ internet }: { internet: Evidence["internet"] }) {
  return <>
    <Rows rows={[
      { label: "Reachability", value: internet.status },
      { label: "Targets measured", value: internet.tested },
      { label: "Targets that responded", value: internet.reached },
      ...(internet.error ? [{ label: "Details", value: internet.error }] : []),
    ]} />
    {internet.probes.length ? <div className="technical-group">
      <table className="probe-table" role="table">
        <caption>Public target comparison</caption>
        <thead role="rowgroup"><tr role="row">
          <th scope="col" role="columnheader">Target</th>
          {probeColumns.map(([key, label]) => <th key={key} scope="col" role="columnheader">{label}</th>)}
        </tr></thead>
        <tbody role="rowgroup">
          {internet.probes.map((probe, index) => <tr key={index} role="row">
            <th scope="row" role="rowheader"><code>{probe.target}</code></th>
            {probeColumns.map(([key, label]) => (
              <td key={key} role="cell"><span className="probe-compact-label" aria-hidden="true">{label}</span>{probe[key]}</td>
            ))}
          </tr>)}
        </tbody>
      </table>
      <details className="probe-details">
        <summary>More per-target details</summary>
        {internet.probes.map((probe, index) => <MeasurementGroup key={index} technicalTitle group={{
          title: probe.target,
          rows: [...probe.latency, ...(probe.error ? [{ label: "Details", value: probe.error }] : [])],
        }} />)}
      </details>
    </div> : <p className="technical-muted technical-group">No per-target observations available.</p>}
  </>;
}

function DnsMeasurements({ dns }: { dns: Evidence["dns"] }) {
  return <>
    <MeasurementGroup group={dns.system} />
    <p className="technical-muted dns-context">Windows may use its cache or DNS policy. This lookup does not identify an upstream resolver or prove it responded live.</p>
    <div className="technical-group">
      <h3>Direct configured resolver queries</h3>
      <Rows rows={[
        { label: "Assessment", value: dns.directStatus },
        { label: "First configured resolver", value: dns.first ?? "Unavailable", technical: true },
      ]} />
      {dns.direct.length ? <ul className="resolver-queries">
        {dns.direct.map((query, index) => <li key={index}><code>{query.title}</code><Rows rows={query.rows} /></li>)}
      </ul> : <p className="technical-muted">No direct query observations available.</p>}
    </div>
    {dns.additional.length > 0 && <div className="technical-group">
      <h3>Additional direct queries</h3>
      <ul className="resolver-queries">
        {dns.additional.map((query, index) => <li key={index}><code>{query.title}</code><Rows rows={query.rows} /></li>)}
      </ul>
    </div>}
    {dns.primaryInventory.length > 0 && <div className="technical-group">
      <h3>Primary-interface resolver inventory</h3>
      <Rows rows={dns.primaryInventory} />
    </div>}
    <div className="technical-group">
      <h3>Off-interface resolver inventory</h3>
      {dns.otherInventory.length ? <Rows rows={dns.otherInventory} />
        : <p className="technical-muted">No off-interface resolver observations available.</p>}
      <p className="technical-muted dns-context">Inventory records interface and route observations. A matching route alone does not establish resolver selection.</p>
    </div>
    {dns.unknownInventory.length > 0 && <div className="technical-group">
      <h3>Unattributed resolver inventory</h3>
      <Rows rows={dns.unknownInventory} />
    </div>}
    {(dns.attr || dns.error) && <div className="technical-group">
      <h3>Attribution and limitations</h3>
      <Rows rows={[
        ...(dns.attr ? [{ label: "Attribution", value: dns.attr }] : []),
        ...(dns.error ? [{ label: "Details", value: dns.error }] : []),
      ]} />
    </div>}
  </>;
}

function jumpToSection(id: SectionKey) {
  const heading = document.getElementById(`evidence-${id}`);
  heading?.focus({ preventScroll: true });
  heading?.scrollIntoView({ block: "start" });
}

export function TechnicalEvidence({ details, findings, onBack }: {
  details: DiagnosticDetails; findings: string[]; onBack: () => void;
}) {
  const evidence = evidenceDetails(details);
  const engineFindings = Array.isArray(findings)
    ? findings.filter(item => typeof item === "string" && item.trim().length > 0)
    : [];
  return (
    <section className="workspace-view technical-workspace checkline-evidence">
      <header className="checkline-evidence-header">
        <div className="checkline-evidence-intro">
          <p className="checkline-evidence-overline">The details behind your result</p>
          <h1 tabIndex={-1}>Technical evidence</h1>
          <p className="checkline-evidence-lede">Review the measurements, sources and limitations from this connection check.</p>
        </div>
        <button className="button button-secondary checkline-evidence-back" type="button" onClick={onBack}>Back to result</button>
      </header>
      <div className="checkline-evidence-layout">
        <nav className="technical-nav checkline-evidence-index" aria-label="Evidence sections">
          <p className="checkline-evidence-index-title">Jump to a section</p>
          {evidenceSections.map(([id, label], index) => (
            <button key={id} className="checkline-evidence-index-link" type="button" onClick={() => jumpToSection(id)}>
              <span aria-hidden="true" className="checkline-evidence-index-number">{String(index + 1).padStart(2, "0")}</span>
              {label}
            </button>
          ))}
          <p className="checkline-evidence-index-help">Evidence is from one investigation, not continuous monitoring.</p>
        </nav>
        <div className="checkline-evidence-document">
          {engineFindings.length > 0 && <section className="checkline-evidence-findings" aria-labelledby="evidence-findings-heading">
            <h2 id="evidence-findings-heading">Diagnosis findings</h2>
            <ul className="findings">{engineFindings.map((item, index) => <li key={index}>{item}</li>)}</ul>
          </section>}
          <EvidenceSection id="device" label="Device" notes={evidence.notes.device}>
            {evidence.device.map(group => <MeasurementGroup key={group.title} group={group} />)}
          </EvidenceSection>
          <EvidenceSection id="local-network" label="Local network" notes={evidence.notes["local-network"]}>
            {evidence.localNetwork.map(group => <MeasurementGroup key={group.title} group={group} />)}
          </EvidenceSection>
          <EvidenceSection id="internet" label="Internet" notes={evidence.notes.internet}>
            <InternetMeasurements internet={evidence.internet} />
          </EvidenceSection>
          <EvidenceSection id="dns" label="DNS" notes={evidence.notes.dns}>
            <DnsMeasurements dns={evidence.dns} />
          </EvidenceSection>
          {evidence.notes.unscoped.length > 0 && <section className="checkline-evidence-extra-notes" aria-label="Other collection notes">
            <SectionNotes notes={evidence.notes.unscoped} heading="h2" />
          </section>}
        </div>
      </div>
    </section>
  );
}
