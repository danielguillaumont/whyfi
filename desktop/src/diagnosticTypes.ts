import type { DnsResolverEvidence, SystemDnsQuery } from "./dnsEvidence";

export type Diagnosis = {
  code: string;
  title: string;
  confidence: number | null;
  summary: string;
  evidence: string[];
  recommendation: string | null;
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
  error?: string | null;
};

type DnsDetails = {
  healthy?: boolean | null;
  default_resolver?: string | null;
  default_query?: DnsQueryDetails | null;
  likely_dns_issue?: boolean | null;
  configured_queries?: DnsQueryDetails[];
  resolver_evidence?: DnsResolverEvidence[];
  system_query?: SystemDnsQuery | null;
  attribution_error?: string | null;
  error?: string | null;
};

type WifiDetails = {
  connected?: boolean | null;
  interface_name?: string | null;
  signal_percent?: number | null;
  radio_type?: string | null;
  channel?: number | null;
  receive_rate_mbps?: number | null;
  transmit_rate_mbps?: number | null;
  error?: string | null;
};

type LocalConfigDetails = {
  healthy?: boolean | null;
  active_adapters?: string[] | null;
  usable_ipv4_adapters?: string[] | null;
  link_local_ipv4_adapters?: string[] | null;
  likely_dhcp_issue?: boolean | null;
};

export type DiagnosticDetails = {
  connection?: ConnectionDetails | null;
  gateway?: PingDetails | null;
  internet?: InternetDetails | null;
  dns?: DnsDetails | null;
  wifi?: WifiDetails | null;
  local_config?: LocalConfigDetails | null;
  collection_errors?: { check: string; target?: string | null; message: string }[];
  completed?: boolean | null;
  error?: string | null;
};

export type ResultEvent = {
  type: "result";
  diagnosis: Diagnosis;
  details: DiagnosticDetails;
};
