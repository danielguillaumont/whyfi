import assert from "node:assert/strict";
import { after, test } from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

const vite = await createServer({
  mode: "production",
  server: { middlewareMode: true, ws: false, watch: null },
  optimizeDeps: { noDiscovery: true, include: [] },
});
after(() => vite.close());

const { DiagnosisScreen } = await vite.ssrLoadModule("/src/DiagnosisScreen.tsx");
const { ResultOverview } = await vite.ssrLoadModule("/src/ResultOverview.tsx");
const { TechnicalEvidence } = await vite.ssrLoadModule("/src/TechnicalEvidence.tsx");
const render = (Component, props) => renderToStaticMarkup(createElement(Component, props));

test("Cancel is natively disabled before acknowledgement and keeps a focusable button during cancellation", () => {
  const button = state => render(DiagnosisScreen, {
    state: { phase: "running", progress: "Current step", ...state },
  }).match(/<button[^>]*>Cancel<\/button>/)[0];
  assert.match(button({ canCancel: false, cancelling: false }), / disabled=""/);
  const pending = button({ canCancel: false, cancelling: true });
  assert.match(pending, / aria-disabled="true"/);
  assert.doesNotMatch(pending, / disabled=/);
  assert.doesNotMatch(button({ canCancel: true, cancelling: false }), /disabled/);
});

test("cancellation has a focused heading and preserves a cleanup notice without repeating the default outcome", () => {
  const cancelled = message => render(DiagnosisScreen, { state: { phase: "cancelled", message } });
  const normal = cancelled("Investigation cancelled.");
  assert.match(normal, /<h1 tabindex="-1">Investigation cancelled<\/h1>/);
  assert.doesNotMatch(normal, /diagnosis-notice|role="status"/);
  assert.match(cancelled("Investigation cancelled. Cleanup is pending."), /<span>Cleanup is pending\.<\/span>/);
  assert.match(normal, /Start diagnosis/);
});

test("the Result heading exposes the visible status as its accessible description", () => {
  for (const [code, label] of [
    ["healthy", "Healthy"], ["gateway_issue", "Problem found"], ["unknown", "Inconclusive"],
  ]) {
    const markup = render(ResultOverview, {
      diagnosis: { code, title: "Engine conclusion", summary: "Summary", confidence: null },
      details: null,
    });
    assert.match(markup, /<h1 tabindex="-1" aria-describedby="diagnosis-outcome">Engine conclusion<\/h1>/);
    assert.match(markup, new RegExp('id="diagnosis-outcome"[^>]*>.*</span>' + label + '</span>'));
  }
});

test("Checkline Result renders real zero measurements and an Evidence focus target", () => {
  const markup = render(ResultOverview, {
    diagnosis: { code: "healthy", title: "Everything looks healthy.", summary: "Checks responded.", confidence: 96,
      recommendation: "No action needed." },
    details: {
      completed: true,
      connection: { is_up: true },
      local_config: { healthy: true },
      gateway: { reachable: true, average_latency_ms: 0, packet_loss_percent: 0 },
      internet: { reachable: true, targets_tested: 2, targets_reachable: 2 },
      dns: { default_resolver: "192.0.2.53", default_query: { success: true } },
    },
  });
  assert.match(markup, /aria-label="Results by investigation area"/);
  assert.match(markup, /Device[\s\S]*Local network[\s\S]*Internet[\s\S]*DNS/);
  assert.match(markup, /0 ms average latency/);
  assert.match(markup, /0 % packet loss/);
  assert.match(markup, /192\.0\.2\.53/);
  assert.match(markup, /Rule-based engine score/);
  assert.match(markup, /Not a probability of correctness/);
  assert.match(markup, /data-evidence-entry/);
  assert.match(markup, /No action needed\./);
});

test("Checkline Result distinguishes failed from unavailable checks", () => {
  const markup = render(ResultOverview, {
    diagnosis: { code: "unknown", title: "Not enough information", summary: "Some tests could not run.",
      confidence: null, recommendation: "Try again later." },
    details: {
      completed: false,
      connection: { is_up: true },
      local_config: { healthy: true },
      gateway: { reachable: false, average_latency_ms: null, packet_loss_percent: 100 },
      internet: { reachable: null, targets_tested: 0, targets_reachable: 0 },
      dns: { default_query: null },
    },
  });
  assert.match(markup, /Inconclusive/);
  assert.match(markup, /checkline-result-check-problem/);
  assert.match(markup, /checkline-result-check-unavailable/);
  assert.match(markup, /checkline-result-check-not-assessed/);
  assert.match(markup, /Average latency unavailable/);
  assert.match(markup, /100 % packet loss/);
  assert.doesNotMatch(markup, /Rule-based engine score/);
});

test("development previews do not fabricate Checkline measurements or expose Evidence", () => {
  const markup = render(ResultOverview, {
    diagnosis: { code: "dns_issue", title: "A DNS issue", summary: "A preview.",
      confidence: 70, recommendation: "Review DNS settings." },
    details: null,
  });
  assert.match(markup, /Development preview/);
  assert.doesNotMatch(markup, /Results by investigation area|View evidence|data-evidence-entry/);
  assert.match(markup, /Review DNS settings\./);
  assert.match(markup, /Run another check/);
});


test("Checkline Evidence preserves navigation destinations, full sections and the back action", () => {
  const markup = render(TechnicalEvidence, {
    details: {}, findings: ["Windows evidence was collected."], onBack: () => {},
  });
  assert.match(markup, /aria-label="Evidence sections"/);
  for (const area of ["device", "local-network", "internet", "dns"]) {
    assert.match(markup, new RegExp('id="evidence-' + area + '" tabindex="-1"'));
  }
  assert.match(markup, /Back to result/);
  assert.match(markup, /Windows evidence was collected/);
  assert.match(markup, /Not assessed|Unavailable/);
});

test("Checkline Evidence preserves measured zero, DNS attribution and real table headings", () => {
  const markup = render(TechnicalEvidence, {
    details: {
      connection: { adapter_name: "Wi-Fi", interface_index: 20, ipv4_address: "192.0.2.11", is_up: true },
      gateway: { target: "192.0.2.1", reachable: true, average_latency_ms: 0, packet_loss_percent: 0 },
      internet: { reachable: true, targets_tested: 1, targets_reachable: 1, probes: [
        { target: "198.51.100.1", reachable: true, average_latency_ms: 0, packet_loss_percent: 0, packets_sent: 4, packets_received: 4 },
      ] },
      dns: {
        system_query: { hostname: "example.com", success: true },
        default_resolver: "192.0.2.53",
        configured_queries: [{ resolver: "192.0.2.53", success: false, error: "Lookup failed" }],
      },
    },
    findings: [], onBack: () => {},
  });
  assert.match(markup, /0 ms/);
  assert.match(markup, /0%/);
  assert.match(markup, /198\.51\.100\.1/);
  assert.match(markup, /<caption>Public target comparison<\/caption>/);
  assert.match(markup, /scope="col"[^>]*>Avg\. latency<\/th>/);
  assert.match(markup, /Windows may use its cache or DNS policy/);
  assert.match(markup, /Direct configured resolver queries/);
  assert.match(markup, /192\.0\.2\.53/);
  assert.match(markup, /Lookup failed/);
});
