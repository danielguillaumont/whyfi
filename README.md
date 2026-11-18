# WHYFI

> **Shazam for broken internet.**

WHYFI is a Windows network diagnostic application that investigates connectivity problems, identifies the most likely failure point, and explains what is happening in plain language.

Instead of making users understand DNS, DHCP, gateways, packet loss, jitter, or routing, WHYFI collects the evidence automatically and answers:

> **Why isn't my internet working properly?**

---

## Current Status

🚧 **Active Development — Functional Windows desktop application**

WHYFI currently includes:

- Native Windows desktop application
- Standalone Windows installer
- Bundled Python diagnostic engine
- Evidence-based root-cause diagnosis
- Real-time diagnostic progress
- Plain-language results and recommendations
- Expandable technical measurements
- Command-line interface
- Connection-quality analysis
- Development previews for failure scenarios
- Automated pytest coverage and GitHub Actions CI

The installed application runs independently without requiring Python, npm, Cargo, VS Code, or the source repository.

---

## What WHYFI Diagnoses

WHYFI investigates the connection layer by layer:

```text
Windows Device
      ↓
Adapter + IPv4 / DHCP
      ↓
Wi-Fi + Local Gateway
      ↓
Internet Connectivity
      ↓
DNS
      ↓
Evidence Analysis
      ↓
Diagnosis + Confidence + Recommendation
```

Current checks include:

- Network adapters
- Primary connection
- IPv4 configuration
- DHCP / APIPA problems
- Default gateway
- Wi-Fi signal and link information
- Gateway reachability
- Internet reachability
- DNS resolution
- Latency
- Packet loss
- Jitter
- Local vs upstream instability

### Diagnosis Types

```text
healthy
no_connection
local_config_issue
gateway_issue
internet_issue
dns_issue
wifi_issue
unstable_connection
unknown
```

WHYFI deliberately combines multiple signals before making a diagnosis.

For example, weak Wi-Fi alone does not automatically mean Wi-Fi is the problem, and one unstable public endpoint does not automatically mean the internet connection is unstable.

---

## Desktop Experience

The main workflow is intentionally simple:

```text
READY
  ↓
DIAGNOSING
  ↓
RESULT
```

The user presses:

> **Diagnose**

WHYFI then streams real diagnostic progress into the interface:

```text
Checking network configuration...
Finding your active connection...
Checking your router...
Checking Wi-Fi signal...
Testing internet access...
Checking DNS...
```

The final result includes:

- Diagnosis
- Confidence score
- Plain-language summary
- Supporting evidence
- Recommended next action
- Optional technical details

Example:

```text
Everything looks healthy.

96% confidence

Your local connection, router, internet access,
and DNS are all responding normally.

Evidence:
- Primary adapter: Wi-Fi
- Gateway reachable with 0% packet loss
- Public targets reachable: 2/2
- DNS responded successfully
- Wi-Fi signal is good
- Local IPv4 configuration is healthy

Recommendation:
No action is needed.
```

---

## Technical Details

Advanced users can expand the result to inspect measurements without cluttering the main experience.

WHYFI can display:

**Connection**
- Adapter
- Connection type
- IPv4 address
- Gateway
- Link state
- Link speed
- MTU

**Gateway / Internet**
- Reachability
- Latency
- Packet loss
- Jitter
- Per-target measurements

**DNS**
- Resolver health
- Resolver address
- Query latency
- DNS issue detection

**Wi-Fi**
- Signal strength
- Radio type
- Channel
- Receive / transmit rate

**Local configuration**
- Configuration health
- DHCP issue detection
- Active adapters
- Usable IPv4 adapters

---

## Architecture

```text
React + TypeScript
        ↓
Tauri / Rust
        ↓
Bundled WHYFI Sidecar
        ↓
Python Diagnostic Engine
        ↓
Windows Network Measurements
        ↓
Structured JSON Events
        ↓
Live Progress + Result
```

The Rust bridge runs the bundled Python engine with `--stream-json`.
The engine writes UTF-8-compatible newline-delimited JSON to stdout and flushes
each event. LF and CRLF line endings are accepted. The stream has zero or more
progress events followed by exactly one terminal event. Blank lines are ignored:

| `type` | Payload | Meaning |
| --- | --- | --- |
| `progress` | `message` string | Status update forwarded to the desktop. |
| `result` | `diagnosis` and `details` objects | Final diagnosis, including inconclusive diagnoses and probe failures recorded in technical details. A successful stream exits with status 0. |
| `error` | `message` string | Fatal engine error. The CLI emits this event and exits with status 1. |

Rust buffers raw stdout bytes until it has a complete line. It validates the
event type, required diagnosis fields, and the technical fields rendered by
React. Unavailable measurements may be null, and additional engine fields pass
through. The Python event format is shared by the CLI and desktop.

Each stdout record may contain up to **1 MiB (1,048,576 bytes)** before the
LF delimiter, including any preceding CR. This leaves room for a full diagnostic
snapshot and also bounds incomplete lines. The bridge retains the first
**8 KiB** of stderr for error context and marks the displayed excerpt if more
was discarded.

Malformed JSON, invalid UTF-8, unknown event types, an unfinished line, extra
events after the terminal event, a missing result, or an unsuccessful process
exit produces a failed investigation. An oversized record also fails the
investigation. Stderr is diagnostic output outside the protocol and can provide
context for a failed exit when there is no structured error event.

### Investigation lifecycle

The desktop uses `start_diagnosis` to reserve the single active investigation
and receive its run ID and progress through a per-invocation Tauri channel. The
command returns a terminal outcome with the same run ID. `cancel_diagnosis`
accepts only that active ID. Cancellation accepted before the worker claims a
terminal outcome wins over a late result. React ignores events from previous
investigations and displays cancellation, timeout, and failure separately.

Set `WHYFI_INVESTIGATION_TIMEOUT_SECONDS` in the desktop process environment
before launch to override the **120-second** overall deadline. The accepted
range is 5–600 whole seconds. This budget starts when Rust admits the run,
includes sidecar startup, and reserves the final three seconds for cleanup.
Once the work deadline expires, the worker requests termination even if the
sidecar has produced no output.

The bridge uses Tauri's packaged sidecar resolver and supervises the resolved
command through its owned OS process handle. It polls direct-child exit
independently of stdout and stderr. It reads available bytes without waiting
for pipe EOF or leaving background pipe readers. On cancellation, timeout, or
a protocol error it closes the read handles and requests direct-child
termination on a blocking worker. A kill request alone does not release the
run slot. If cleanup exceeds the deadline, the outcome returns while the
worker keeps the slot reserved until it confirms exit. Cleanup errors are
included when available and logged if they occur after the outcome.

Windows descendants, including helpers launched by the packaged Python
executable, can outlive the direct child. Inherited writer handles cannot
delay exit confirmation or keep WHYFI's readers alive. The bridge does not
terminate the process tree. If the OS never confirms direct-child exit,
the app keeps new investigations blocked.

CI tests the Rust lifecycle with synthetic process events and the React run
guard with Node's test runner. For a packaged Windows smoke test, complete a
normal investigation, cancel during progress and retry, exercise cancellation
near completion, and run with a short deadline override. Check Task Manager
for lingering child processes after cancellation or timeout.

The deterministic network engine remains the source of truth.

### Desktop security

The packaged WebView uses Tauri's Content Security Policy. It denies resources
by default, permits scripts, styles, and images from the bundled app origin,
and limits connections to Tauri IPC (`ipc:` and `http://ipc.localhost`).
Tauri can add hashes and nonces for bundled content. The production policy
omits both `unsafe-inline` and `unsafe-eval`. Tauri's separate
development policy permits inline code for Vite tooling and loopback HMR on
port 1420. Treat the development server as a trusted local tool.

Only the local `main` window receives the investigation permission.
It can start the fixed bundled `whyfi-engine --stream-json` sidecar or cancel
the matching active run. Progress uses a Tauri IPC channel. The WebView has no
generic shell, filesystem, URL-opening, or broad core permissions. The Rust
shell plugin supplies the packaged sidecar path without granting shell commands
to the frontend.

The desktop does not upload diagnostic reports or send application telemetry.
The engine still makes the DNS and ICMP probes needed for diagnosis. Those
destinations and the configured DNS service can observe their respective
queries. Technical details can contain adapter names, addresses, resolver
information, and local errors. Keep that in mind when sharing results.
These protections scope WebView access. The native application and its
sidecar still run with the Windows user's privileges. Configuration tests and
Cargo validation check policy and permission definitions. Windows runtime
verification checks rendering, assets, and diagnosis IPC separately.

---

## Standalone Windows Packaging

WHYFI's Python diagnostic engine is packaged into a standalone executable using **PyInstaller** and bundled with the Tauri desktop application as a sidecar.

The production build automatically performs:

```text
Build Python diagnostic sidecar
        ↓
Build React frontend
        ↓
Compile Rust / Tauri application
        ↓
Bundle diagnostic engine
        ↓
Create Windows installers
```

Current installer outputs:

```text
whyfi_0.1.0_x64_en-US.msi
whyfi_0.1.0_x64-setup.exe
```

The installer has been tested successfully: the installed application launches the bundled diagnostic engine, performs a real network investigation, streams progress, and displays the final result without requiring a Python environment.

---

## CLI

WHYFI can also run directly from the terminal.

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

- `diagnosis.confidence` is a percentage when assigned and `null` when
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
  resolver answers, `false` when all measured lookups fail, and `null` when
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

---

## Testing

Run the suite with:

```powershell
python -m pytest -q
```

Coverage includes:

- Healthy connections
- No connection
- DHCP / APIPA failure
- Gateway failure
- Internet failure
- DNS failure
- Wi-Fi issues
- Packet loss
- Gateway and public jitter
- Local vs upstream instability
- Ambiguous / unknown diagnoses
- Conservative multi-signal diagnosis rules
- CLI behavior
- JSON output
- Streaming progress

All current diagnosis codes are covered by automated tests.

### Continuous integration

The [CI workflow](.github/workflows/ci.yml) runs on pull requests targeting
`main`, pushes to `main`, and manual dispatch from the Actions tab.

| Check | Runner | Verification |
| --- | --- | --- |
| Python | Windows, Python 3.12 | Installs WHYFI and pytest, checks Python syntax, and runs the full suite. Windows probes are covered by deterministic mocks and fixtures. |
| Frontend | Ubuntu, Node 22 | Installs from the npm lockfile, type-checks the Vite config, and runs the application TypeScript and Vite build. |
| Rust / Tauri | Windows, stable Rust | Runs rustfmt, checks all locked Cargo targets, and runs the Rust library tests with synthetic sidecar streams. Step-local Tauri overrides clear `externalBin` so both Cargo commands can run on a clean checkout. |

CI caches dependency downloads. Every run still installs or resolves dependencies
and runs the checks. The workflow uses read-only repository permissions and
cancels superseded runs on the same ref.

The Rust checks use the development configuration. The protocol tests feed
synthetic byte streams into the parser without launching a packaged sidecar.
Live Windows diagnostics, real sidecar transport, installer builds, and
installed-app behavior remain separate verification steps.

---

## Technology

### Diagnostic Engine
- Python 3.12
- psutil
- dnspython
- Windows networking utilities
- ping
- netsh
- pytest
- PyInstaller

### Desktop
- Tauri 2
- Rust
- React 19
- TypeScript
- Vite
- Windows WebView
- Custom CSS

### Tooling
- Git / GitHub
- Node.js / npm
- Cargo
- Visual Studio Build Tools
- Windows SDK

---

## Development

Create the Python environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Run the desktop application:

```powershell
cd desktop
npm install
npm run tauri dev
```

Build the complete Windows application:

```powershell
npm run tauri build
```

The Tauri build automatically rebuilds the Python sidecar before compiling and packaging the desktop application.

---

## Roadmap

### Diagnostic Engine
- [x] Adapter and route discovery
- [x] IPv4 / DHCP diagnostics
- [x] Gateway diagnostics
- [x] Internet reachability
- [x] DNS diagnostics
- [x] Wi-Fi diagnostics
- [x] Latency, packet loss, and jitter
- [x] Local vs upstream instability
- [x] Evidence-based diagnosis
- [x] Confidence scoring
- [x] Automated scenario coverage
- [ ] Additional Windows edge cases
- [ ] More resilient command parsing
- [ ] Confidence calibration

### Desktop Application
- [x] Tauri + React application
- [x] Rust backend bridge
- [x] Real-time diagnostic progress
- [x] Result / evidence / recommendation UI
- [x] Technical-details view
- [x] Healthy / problem / unknown states
- [x] Development failure previews
- [x] Bundled diagnostic engine
- [x] Standalone Windows installer
- [x] Automated sidecar build
- [ ] Additional UI polish
- [ ] Broader real-world failure testing

### Toward V1.0
- [x] Standalone MSI installer
- [x] Standalone setup EXE
- [x] Production sidecar bridge
- [x] Automated production build
- [ ] Broader Windows compatibility testing
- [ ] Privacy sanitization layer
- [x] CI pipeline
- [ ] GitHub release
- [ ] Product screenshots
- [ ] Demo video

---

## Design Philosophy

WHYFI should be technically deep underneath but extremely simple for the person using it.

The product should require:

- No account
- No login
- No cloud dashboard
- No networking knowledge
- No complicated configuration
- One primary action: **Diagnose**

The intended experience is:

> Press Diagnose.  
> Wait a few seconds.  
> Understand what is wrong.

---

## AI Direction

AI is intentionally **not** the foundation of WHYFI.

The deterministic engine comes first so the application can still diagnose connectivity problems when the internet itself is unavailable.

A future AI layer may help with:

- Ambiguous diagnoses
- Guided follow-up investigation
- Natural-language explanations
- Selecting additional safe diagnostic tools

But measurable network evidence will remain the source of truth.

---

## Next

The core diagnostic engine, desktop application, sidecar packaging, and Windows installer now work end-to-end.

The next phase is focused on:

```text
Real-world failure testing
        ↓
Windows compatibility hardening
        ↓
UI polish
        ↓
Privacy / sanitization
        ↓
CI + public release
```
