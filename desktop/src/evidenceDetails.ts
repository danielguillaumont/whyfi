import type { DiagnosticDetails } from "./diagnosticTypes";
import { evidenceCollectionNotes } from "./collectionNotes.ts";
import { resolverEvidenceRows } from "./dnsEvidence.ts";

export const evidenceSections = [
  ["device", "Device"], ["local-network", "Local network"], ["internet", "Internet"], ["dns", "DNS"],
] as const;

type RecordData = Record<string, unknown>;
type Row = { label: string; value: string; technical?: boolean };
type Group = { title: string; rows: Row[]; note?: string };
const unavailable = "Unavailable";

function record(value: unknown): RecordData | undefined {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? value as RecordData : undefined;
}

function records(value: unknown) {
  return Array.isArray(value) ? value.flatMap(item => {
    const entry = record(item);
    return entry ? [entry] : [];
  }) : [];
}

function string(value: unknown) {
  return typeof value === "string" && value.trim() ? value : undefined;
}

function metric(value: unknown, unit = "") {
  return typeof value === "number" && Number.isFinite(value) && value >= 0
    ? `${value}${unit}` : unavailable;
}

function status(value: unknown, positive: string, negative: string) {
  return value === true ? positive : value === false ? negative : unavailable;
}

function list(value: unknown) {
  if (!Array.isArray(value)) return unavailable;
  const items = value.flatMap(item => string(item) ?? []);
  return items.length ? items.join(", ") : value.length === 0 ? "None reported" : unavailable;
}

function row(label: string, value: string | undefined, technical = false): Row {
  return { label, value: value ?? unavailable, technical };
}

function absent(title: string, skipped: boolean): Group {
  return { title, rows: [], note: skipped ? "Not assessed" : unavailable };
}

function probe(value: RecordData) {
  return {
    target: string(value.target) ?? unavailable,
    status: status(value.reachable, "Responded", "No reply"),
    average: metric(value.average_latency_ms, " ms"),
    loss: metric(value.packet_loss_percent, "%"),
    sent: metric(value.packets_sent),
    received: metric(value.packets_received),
    error: string(value.error),
  };
}

function latencyRows(value: RecordData) {
  return [
    row("Minimum latency", metric(value.min_latency_ms, " ms")),
    row("Maximum latency", metric(value.max_latency_ms, " ms")),
    row("Jitter", metric(value.jitter_ms, " ms")),
  ];
}

function queryRows(value: RecordData): Row[] {
  const error = string(value.error);
  return [
    row("Test name", string(value.hostname), true),
    row("Lookup", status(value.success, "Resolved", "Lookup failed")),
    row("Addresses returned", list(value.addresses), true),
    ...(error ? [row("Details", error)] : []),
  ];
}

export function evidenceDetails(details: DiagnosticDetails) {
  const connection = record(details.connection);
  const local = record(details.local_config);
  const wifi = record(details.wifi);
  const gateway = record(details.gateway);
  const internet = record(details.internet);
  const dns = record(details.dns);
  const notes = evidenceCollectionNotes(details.collection_errors, details.error);
  const noPrimary = details.connection === null && !notes.device.some(note => note.kind === "route" || note.kind === "route_consistency");
  const device: Group[] = [
    connection ? { title: "Primary adapter", rows: [
      row("Adapter", string(connection.adapter_name), true),
      row("Interface index", metric(connection.interface_index), true),
      row("Type", string(connection.adapter_type)),
      row("IPv4 address", string(connection.ipv4_address), true),
      row("Default gateway", string(connection.gateway), true),
      row("Link state", status(connection.is_up, "Up", "Down")),
      row("Reported link speed", metric(connection.speed_mbps, " Mbps")),
      row("MTU", metric(connection.mtu, " bytes")),
    ] } : absent("Primary adapter", false),
    local ? { title: "Local IP configuration", rows: [
      row("Configuration", status(local.healthy, "Passed", "Failed")),
      row("Likely DHCP issue", status(local.likely_dhcp_issue, "Yes", "No")),
      row("Active adapters", list(local.active_adapters), true),
      row("Usable IPv4 adapters", list(local.usable_ipv4_adapters), true),
      row("Link-local IPv4 adapters", list(local.link_local_ipv4_adapters), true),
    ] } : absent("Local IP configuration", false),
  ];

  const gatewayProbe = gateway && probe(gateway);
  const localNetwork: Group[] = [
    gatewayProbe && gateway ? { title: "Default gateway", rows: [
      row("Target", gatewayProbe.target, true),
      row("Reachability", gatewayProbe.status),
      row("Average latency", gatewayProbe.average),
      row("Packet loss", gatewayProbe.loss),
      row("Packets sent", gatewayProbe.sent),
      row("Packets received", gatewayProbe.received),
      ...latencyRows(gateway),
      ...(gatewayProbe.error ? [row("Details", gatewayProbe.error)] : []),
    ] } : absent("Default gateway", noPrimary && details.gateway === null && !notes["local-network"].some(note => note.kind === "gateway")),
    wifi ? { title: "Wi-Fi", rows: [
      row("Connection", status(wifi.connected, "Connected", "Disconnected")),
      row("Interface", string(wifi.interface_name), true),
      row("Signal", metric(wifi.signal_percent, "%")),
      row("Radio", string(wifi.radio_type)),
      row("Channel", metric(wifi.channel)),
      row("Reported receive rate", metric(wifi.receive_rate_mbps, " Mbps")),
      row("Reported transmit rate", metric(wifi.transmit_rate_mbps, " Mbps")),
      ...(string(wifi.error) ? [row("Details", string(wifi.error))] : []),
    ] } : {
      title: "Wi-Fi", rows: [],
      note: notes["local-network"].some(note => note.kind === "wifi")
        ? unavailable
        : details.wifi === null && connection?.adapter_type === "ethernet" ? "Not applicable to the primary Ethernet link"
        : absent("Wi-Fi", noPrimary && details.wifi === null).note,
    },
  ];

  const system = record(dns?.system_query);
  const first = record(dns?.default_query);
  const configured = records(dns?.configured_queries);
  const direct = configured.length ? configured : first ? [first] : [];
  const inventory = Array.isArray(details.dns?.resolver_evidence)
    ? details.dns.resolver_evidence.filter(item => record(item)) : [];
  const attr = string(dns?.attribution_error);
  const dnsError = string(dns?.error);
  return {
    device, localNetwork, notes,
    internet: {
      status: status(internet?.reachable, "At least one target responded", "No target responded"),
      tested: internet?.targets_tested === 0 && internet.reachable == null ? "No completed measurements" : metric(internet?.targets_tested),
      reached: internet?.targets_tested === 0 && internet.reachable == null ? unavailable : metric(internet?.targets_reachable),
      probes: records(internet?.probes).map(value => ({ ...probe(value), latency: latencyRows(value) })),
      error: string(internet?.error),
    },
    dns: {
      system: system ? { title: "Windows DNS-client lookup", rows: queryRows(system) }
        : absent("Windows DNS-client lookup", false),
      first: string(dns?.default_resolver),
      directStatus: status(dns?.healthy, "At least one configured resolver resolved", "Configured resolver assessment failed"),
      direct: direct.map(query => ({
        title: string(query.resolver) ?? (query === first ? string(dns?.default_resolver) : undefined) ?? "Resolver unavailable",
        rows: [...queryRows(query), row("Lookup latency", metric(query.latency_ms, " ms"))],
      })),
      additional: records(dns?.alternate_queries).map(query => ({
        title: string(query.resolver) ?? "Resolver unavailable",
        rows: [...queryRows(query), row("Lookup latency", metric(query.latency_ms, " ms"))],
      })),
      primaryInventory: resolverEvidenceRows(inventory.filter(item => item.primary === true)),
      otherInventory: resolverEvidenceRows(inventory.filter(item => item.primary === false)),
      unknownInventory: resolverEvidenceRows(inventory.filter(item => typeof item.primary !== "boolean")),
      attr, error: dnsError === attr ? undefined : dnsError,
    },
  };
}
