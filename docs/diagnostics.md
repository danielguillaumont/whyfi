# WHYFI command-line diagnostics

After the development install, activate the project virtual environment to use the commands below. From the repository root, you can also invoke the CLI as `.\.venv\Scripts\python.exe -m whyfi` with the same options.

```powershell
whyfi
```

Deeper connection-quality testing:

```powershell
whyfi --quality
```

Technical measurements:

```powershell
whyfi --details
```

Structured output:

```powershell
whyfi --json
```

Streaming structured output:

```powershell
whyfi --stream-json
```

`--json` prints a single object with `diagnosis` and `details`.
`--stream-json` prints one JSON object per line, with `type: "progress"`
for progress messages and `type: "result"` for the final object carrying
the same `diagnosis` and `details`. A fatal streaming failure emits
`{"type":"error","message":"..."}` and exits nonzero.

- `diagnosis.confidence` is a rule-based score from 0 to 100 when assigned and `null` when
  WHYFI cannot assign a confidence score.
- ICMP `reachable` is `true` for a confirmed reply, `false` for a
  completed measurement with no replies, and `null` when reachability
  could not be determined. Unavailable probes have `null` packet counts
  and packet loss. A completed probe with no replies reports zero packets
  received and 100% loss. Latency and jitter are `null` when there are
  too few replies to calculate them.
- `details.internet.targets_tested` counts targets with a completed
  ICMP measurement. Unavailable targets remain in `details.internet.probes`
  with their error details.
- `details.collection_errors` lists failed collection or consistency
  checks. Each entry has a `check`, a `message`, and a `target` that is
  `null` when the check has no specific probe target.
- `details.wifi.connected` is `false` when the command confirms no
  connected Wi-Fi interface, and `null` when discovery fails or an
  interface cannot be selected reliably. The `error` field explains why.
  WHYFI matches the primary adapter's name when that name is available.
  It requires a recognized interface count and complete records, or a
  recognized message that Windows has no wireless interface. Other formats
  are reported as unavailable.
- On the Windows desktop baseline, `details.dns.configured_queries` contains
  ordered direct query results for distinct resolvers listed on the primary
  interface. `default_resolver` and `default_query` still describe the first
  entry. `healthy` describes the direct test. It is `true` when any queried
  resolver answers, `false` when all configured lookups were measured and failed, and `null` when
  resolution could not be assessed. `likely_dns_issue` requires both paths
  to fail with complete attribution.
- `details.dns.resolver_evidence` preserves resolver records for connected
  interfaces, including `interface_index`, `interface_alias`, `address_family`,
  `resolver`, IPv6 `scope`, `primary`, `route_on_interface`, and
  `provenance`. A matching route is a routing observation. The Windows address
  inventory does not identify how servers were provisioned, so provenance is
  `unknown`. Off-interface addresses, including historical IPv6 entries, stay
  visible in technical details without direct queries. An isolated route to
  an off-interface resolver does not affect the primary DNS assessment.
  These fields are
  additive and existing consumers can continue reading the first resolver.
- `details.dns.system_query` records a separate Windows DNS-client A lookup of
  `example.com.` with an eight-second collection limit. `success` is `true`,
  `false`, or `null` for unavailable evidence. An answer may come from the
  Windows cache or use Windows resolver routing and policy. It does not
  establish live upstream reachability, a particular upstream server, private
  DNS behavior, or encrypted DNS behavior.
- `details.dns.attribution_error` describes missing or ambiguous inventory,
  routes, or namespace policy. Mixed direct results, uncertain attribution,
  and missing or conflicting system results make the DNS assessment
  inconclusive unless independent network evidence identifies a separate
  problem. Unavailable evidence also appears in
  `details.collection_errors`. The Windows baseline does not send comparison
  queries to public DNS resolvers. The legacy `alternate_queries` field remains
  present.

For example, this excerpt from a streaming result shows conflicting route
and public reachability evidence:

```json
{
  "type": "result",
  "diagnosis": {
    "code": "unknown",
    "title": "The diagnosis is inconclusive.",
    "confidence": null,
    "evidence": [
      "No active IPv4 default route was found.",
      "Public IPv4 targets reachable: 2."
    ]
  },
  "details": {
    "connection": null,
    "internet": {"reachable": true, "targets_tested": 2, "targets_reachable": 2},
    "completed": false,
    "collection_errors": [
      {
        "check": "route_consistency",
        "message": "No active IPv4 default route was found, but a public IPv4 target replied.",
        "target": null
      }
    ]
  }
}
```
