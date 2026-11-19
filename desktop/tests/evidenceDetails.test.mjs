import assert from "node:assert/strict";
import test from "node:test";
import { evidenceDetails, evidenceSections } from "../src/evidenceDetails.ts";

test("device and gateway measurements preserve zero, negatives, and explicit units", () => {
  const result = evidenceDetails({
    connection: { interface_index: 20, is_up: false, speed_mbps: 866, mtu: 1500 },
    local_config: { healthy: false, likely_dhcp_issue: false, active_adapters: [] },
    gateway: { reachable: false, average_latency_ms: null, packet_loss_percent: 100, jitter_ms: 0 },
    wifi: { connected: false },
  });
  const rows = group => Object.fromEntries(group.rows.map(({ label, value }) => [label, value]));
  assert.equal(rows(result.device[0])["Interface index"], "20");
  assert.equal(rows(result.device[0])["Link state"], "Down");
  assert.equal(rows(result.device[0])["Reported link speed"], "866 Mbps");
  assert.equal(rows(result.device[0]).MTU, "1500 bytes");
  assert.equal(rows(result.device[1]).Configuration, "Failed");
  assert.equal(rows(result.device[1])["Likely DHCP issue"], "No");
  assert.equal(rows(result.device[1])["Active adapters"], "None reported");
  assert.equal(rows(result.localNetwork[0]).Reachability, "No reply");
  assert.equal(rows(result.localNetwork[0])["Average latency"], "Unavailable");
  assert.equal(rows(result.localNetwork[0])["Packet loss"], "100%");
  assert.equal(rows(result.localNetwork[0]).Jitter, "0 ms");
  assert.equal(rows(result.localNetwork[1]).Connection, "Disconnected");
});

test("keeps measured, failed, unavailable and skipped evidence distinct", () => {
  const result = evidenceDetails({
    connection: null,
    gateway: null,
    wifi: null,
    internet: { reachable: true, targets_tested: 2, targets_reachable: 1, probes: [
      { target: "1.1.1.1", reachable: true, average_latency_ms: 0, packet_loss_percent: 0, packets_sent: 4, packets_received: 4 },
      { target: "8.8.8.8", reachable: false, packet_loss_percent: 100, packets_sent: 4, packets_received: 0 },
      { target: "192.0.2.1", reachable: null, error: "Measurement aborted" },
    ] },
  });
  assert.equal(result.localNetwork[0].note, "Not assessed");
  assert.equal(result.localNetwork[1].note, "Not assessed");
  assert.equal(result.internet.tested, "2");
  assert.equal(result.internet.reached, "1");
  assert.deepEqual(result.internet.probes.map(({ target, status, average, loss, sent, received }) =>
    [target, status, average, loss, sent, received]), [
    ["1.1.1.1", "Responded", "0 ms", "0%", "4", "4"],
    ["8.8.8.8", "No reply", "Unavailable", "100%", "4", "0"],
    ["192.0.2.1", "Unavailable", "Unavailable", "Unavailable", "Unavailable", "Unavailable"],
  ]);
  assert.equal(result.internet.probes[2].error, "Measurement aborted");
  const failedDiscovery = evidenceDetails({
    connection: null, gateway: null, collection_errors: [{ check: "route", message: "Discovery failed" }],
  });
  assert.equal(failedDiscovery.localNetwork[0].note, "Unavailable");
  assert.equal(evidenceDetails({ internet: { reachable: null, targets_tested: 0, targets_reachable: 0 } })
    .internet.tested, "No completed measurements");
});

test("DNS client evidence is separate from the direct query and legacy inventory", () => {
  const result = evidenceDetails({ dns: {
    system_query: { hostname: "example.com", success: true, addresses: ["192.0.2.2"] },
    default_resolver: "192.168.50.1",
    configured_queries: [{ resolver: "192.168.50.1", success: false, error: "No response" }],
    resolver_evidence: [
      { interface_index: 20, interface_alias: "Wi-Fi", address_family: "IPv6", resolver: "fe80::1%20", scope: "20", primary: true, route_on_interface: true, provenance: "unknown" },
      { interface_index: 35, interface_alias: "VMware", address_family: "IPv6", resolver: "fec0:0:0:ffff::1", primary: false, route_on_interface: false },
    ],
    attribution_error: "Policy evidence unavailable",
  } }).dns;
  assert.equal(result.system.rows.find(row => row.label === "Lookup").value, "Resolved");
  assert.equal(result.direct[0].rows.find(row => row.label === "Lookup").value, "Lookup failed");
  assert.match(result.primaryInventory[0].label, /Wi-Fi #20.*fe80::1%20/);
  assert.match(result.primaryInventory[0].value, /Matching interface route.*Scope 20/);
  assert.match(result.otherInventory[0].label, /VMware #35.*fec0/);
  assert.match(result.otherInventory[0].value, /direct query skipped.*No matching interface route.*Provenance: unknown/);
  assert.equal(result.attr, "Policy evidence unavailable");
  assert.equal(evidenceDetails({ dns: { default_resolver: "192.0.2.53", default_query: { success: true } } })
    .dns.direct[0].title, "192.0.2.53");
});

test("rejects malformed nested data and attributes valid collection notes", () => {
  const malformed = { toString: null };
  const result = evidenceDetails({
    connection: ["invalid"],
    gateway: { error: malformed, average_latency_ms: malformed },
    local_config: { active_adapters: [malformed] },
    internet: { probes: [malformed, 8, null, ["invalid"], { target: malformed }] },
    dns: { system_query: "invalid", default_query: [], configured_queries: [false],
      resolver_evidence: [malformed, { interface_index: 5, interface_alias: "Example", address_family: "IPv6", resolver: "fe80::1", primary: malformed }] },
    collection_errors: [
      { check: "dns", target: malformed, message: "Unavailable" },
      { check: "route", message: "Could not collect routes" },
      { check: "custom", message: "Unscoped note" },
      { check: "internet", message: malformed },
    ],
    error: malformed,
  });
  assert.equal(result.device[0].note, "Unavailable");
  assert.equal(result.device[1].rows.find(row => row.label === "Active adapters").value, "Unavailable");
  assert.equal(result.localNetwork[0].rows.find(row => row.label === "Average latency").value, "Unavailable");
  assert.equal(result.internet.probes[1].target, "Unavailable");
  assert.equal(result.dns.system.note, "Unavailable");
  assert.equal(result.dns.direct.length, 0);
  assert.equal(result.dns.otherInventory.length, 0);
  assert.match(result.dns.unknownInventory[0].value, /association unavailable/);
  assert.equal(result.notes.dns[0].label, "dns");
  assert.equal(result.notes.device[0].value, "Could not collect routes");
  assert.equal(result.notes.unscoped[0].label, "custom");
  assert.deepEqual(result.notes.internet, []);
});

test("evidence jump destinations are unique and in reading order", () => {
  assert.deepEqual(evidenceSections.map(([id]) => id), ["device", "local-network", "internet", "dns"]);
});
