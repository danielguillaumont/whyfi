import type { Diagnosis, DiagnosticDetails } from "./diagnosticTypes";

type CheckState = "measured" | "problem" | "unavailable" | "not-assessed";
type Check = { label: string; state: CheckState; status: string; measurements: string[] };

const outcomeLabels = {
  healthy: "Healthy",
  problem: "Problem found",
  inconclusive: "Inconclusive",
};

function number(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value) && value >= 0;
}

function metric(value: unknown, unit: string) {
  return number(value) ? `${value} ${unit}` : undefined;
}

function text(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function check(
  label: string,
  result: unknown,
  available: string,
  failed: string,
  attempted: boolean,
  measurements: string[] = [],
): Check {
  if (result === true) return { label, state: "measured", status: available, measurements };
  if (result === false) return { label, state: "problem", status: failed, measurements };
  return attempted
    ? { label, state: "unavailable", status: "Unavailable", measurements }
    : { label, state: "not-assessed", status: "Not assessed", measurements };
}

export function resultSummary(diagnosis: Diagnosis, details: DiagnosticDetails | null) {
  const tone = diagnosis.code === "healthy" ? "healthy"
    : diagnosis.code === "unknown" ? "inconclusive" : "problem";
  const confidence = number(diagnosis.confidence) && diagnosis.confidence <= 100
    ? `${diagnosis.confidence}/100` : undefined;
  const errors = details?.collection_errors;
  const failedCollection = (name: string) =>
    Array.isArray(errors) && errors.some(row => row?.check === name);

  const local = details?.local_config;
  const connection = details?.connection;
  const linkDown = connection?.is_up === false;
  const device = check("Device", linkDown ? false : local?.healthy,
    "IP settings passed", linkDown ? "Network link down" : "IP settings check failed",
    details !== null);

  const gateway = details?.gateway;
  const latency = metric(gateway?.average_latency_ms, "ms");
  const loss = metric(gateway?.packet_loss_percent, "%");
  const gatewayCheck = check("Gateway", gateway?.reachable, "Responded", "No reply",
    details !== null && (gateway != null || connection !== null || failedCollection("gateway") || failedCollection("route")),
    gateway ? [
      latency === undefined ? "Average latency unavailable" : `${latency} average latency`,
      loss === undefined ? "Packet loss unavailable" : `${loss} packet loss`,
    ] : []);

  const internet = details?.internet;
  const tested = internet?.targets_tested;
  const reached = internet?.targets_reachable;
  const hasCounts = number(tested) && Number.isInteger(tested) && tested > 0
    && number(reached) && Number.isInteger(reached) && reached <= tested;
  const reachability = internet?.reachable;
  const conflictingCounts = hasCounts && ((reachability === true && reached === 0)
    || (reachability === false && reached > 0));
  const partial = reachability === true && hasCounts && reached > 0 && reached < tested;
  const internetCheck = check("Internet", conflictingCounts ? undefined : partial ? false : reachability,
    "Public targets responded", partial ? "Some public targets responded" : "No public targets responded",
    details !== null,
    conflictingCounts ? [] : hasCounts ? [`${reached} of ${tested} measured targets responded`] : []);

  const dns = details?.dns;
  const direct = dns?.default_query;
  const dnsCheck = check("First configured DNS resolver", direct?.success, "Resolved test name",
    "Test name did not resolve", details !== null && (direct !== null || failedCollection("dns")),
    text(dns?.default_resolver) ? [dns.default_resolver] : []);

  const findings: string[] = [];
  const wifi = details?.wifi;
  if (wifi?.connected === true && number(wifi.signal_percent) && wifi.signal_percent <= 100) {
    findings.push(`Wi-Fi signal measured at ${wifi.signal_percent}%.`);
  }
  const systemDns = dns?.system_query?.success;
  if (systemDns === true) findings.push("Windows resolved the test name through its DNS client. The answer may have come from cache.");
  if (systemDns === false) findings.push("The Windows DNS client did not resolve the test name.");
  if (details?.completed === false) findings.push("Some checks could not be completed. See Evidence for details.");

  return {
    tone, status: outcomeLabels[tone], confidence, path: [device, gatewayCheck, internetCheck],
    dns: dnsCheck, findings,
  };
}
