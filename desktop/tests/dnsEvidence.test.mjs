import assert from "node:assert/strict";
import test from "node:test";
import { resolverEvidenceRows, systemDnsSummary } from "../src/dnsEvidence.ts";

test("off-interface evidence shows attribution, scope, and missing route", () => {
  const [row] = resolverEvidenceRows([{
    interface_index: 5,
    interface_alias: "VMware VMnet1",
    address_family: "IPv6",
    resolver: "fec0:0:0:ffff::1%1",
    scope: "1",
    primary: false,
    route_on_interface: false,
    provenance: "unknown",
  }]);
  assert.equal(row.label, "VMware VMnet1 #5 · fec0:0:0:ffff::1%1");
  assert.match(row.value, /Other interface · direct query skipped/);
  assert.match(row.value, /No matching interface route/);
  assert.match(row.value, /Scope 1.*Provenance: unknown/);
});

test("older results and unavailable DNS-client evidence are safe to render", () => {
  assert.deepEqual(resolverEvidenceRows(undefined), []);
  assert.deepEqual(resolverEvidenceRows([null, "unexpected"]), []);
  assert.match(systemDnsSummary({ success: true }), /may have used its cache/);
  assert.match(systemDnsSummary({ success: null, error: "Access denied" }), /Unavailable.*Access denied/);
});
