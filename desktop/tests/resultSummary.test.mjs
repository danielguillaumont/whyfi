import assert from "node:assert/strict";
import test from "node:test";
import { resultSummary } from "../src/resultSummary.ts";

const healthy = { code: "healthy", confidence: 96 };
const details = {
  completed: true,
  connection: { is_up: true },
  local_config: { healthy: true },
  gateway: { reachable: true, average_latency_ms: 3.75, packet_loss_percent: 0 },
  internet: { reachable: true, targets_tested: 2, targets_reachable: 2 },
  dns: {
    default_resolver: "192.0.2.53",
    default_query: { success: true },
    system_query: { success: true },
  },
};

test("healthy results show the engine score, reachability and measured zero", () => {
  const result = resultSummary(healthy, details);
  assert.equal(result.status, "Healthy");
  assert.equal(result.confidence, "96/100");
  assert.deepEqual(result.path.map(check => check.state), ["measured", "measured", "measured"]);
  assert.deepEqual(result.path[1].measurements, ["3.75 ms average latency", "0 % packet loss"]);
  assert.deepEqual(result.path[2].measurements, ["2 of 2 measured targets responded"]);
  assert.equal(result.dns.status, "Resolved test name");
  assert.match(result.findings[0], /may have come from cache/);
});

test("a specific problem keeps measured negatives separate from missing metrics", () => {
  const result = resultSummary({ code: "gateway_issue", confidence: 90 }, {
    ...details,
    gateway: { reachable: false, average_latency_ms: null, packet_loss_percent: 100 },
    internet: { reachable: false, targets_tested: 2, targets_reachable: 0 },
    dns: { default_query: { success: false } },
  });
  assert.equal(result.status, "Problem found");
  assert.equal(result.path[1].status, "No reply");
  assert.deepEqual(result.path[1].measurements, ["Average latency unavailable", "100 % packet loss"]);
  assert.deepEqual(result.path[2].measurements, ["0 of 2 measured targets responded"]);
  assert.equal(result.dns.status, "Test name did not resolve");
});

test("unknown remains inconclusive with nullable, zero or positive confidence", () => {
  for (const [confidence, score] of [[null, undefined], [0, "0/100"], [72, "72/100"]]) {
    const result = resultSummary({ code: "unknown", confidence }, details);
    assert.equal(result.status, "Inconclusive");
    assert.equal(result.confidence, score);
  }
});

test("skipped, unmeasured and partially responsive observations stay distinct", () => {
  const result = resultSummary({ code: "unknown", confidence: null }, {
    completed: false,
    connection: null,
    gateway: null,
    internet: { reachable: null, targets_tested: 0, targets_reachable: 0 },
    dns: { default_query: null },
  });
  assert.deepEqual(result.path.map(check => check.state), ["unavailable", "not-assessed", "unavailable"]);
  assert.deepEqual(result.path[2].measurements, []);
  assert.equal(result.dns.state, "not-assessed");
  assert.match(result.findings[0], /could not be completed/);

  const partial = resultSummary(healthy, {
    internet: { reachable: true, targets_tested: 2, targets_reachable: 1 },
  });
  assert.equal(partial.path[2].status, "Some public targets responded");
});

test("malformed technical values are not formatted or treated as successful", () => {
  const object = { toString: null };
  const result = resultSummary({ code: "unknown", confidence: object }, {
    connection: null,
    gateway: { reachable: object, average_latency_ms: object, packet_loss_percent: null },
    internet: { reachable: true, targets_tested: 2, targets_reachable: 0 },
    dns: { default_resolver: object, default_query: null },
    collection_errors: [null, { check: object }, { check: "dns" }],
  });
  assert.equal(result.confidence, undefined);
  assert.equal(result.path[1].state, "unavailable");
  assert.equal(result.path[2].state, "unavailable");
  assert.equal(result.dns.state, "unavailable");
  assert.deepEqual(result.dns.measurements, []);
});
