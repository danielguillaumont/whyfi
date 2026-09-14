# WHYFI

> Find out why your internet is acting weird.

WHYFI is a Windows network diagnostic application that investigates connectivity problems, identifies the most likely failure point, and explains what is happening in plain language.

Instead of asking users to understand DNS, DHCP, gateways, routing, packet loss, or jitter, WHYFI collects the evidence automatically and answers:

> **Why isn't my internet working properly?**

---

## Current Status

🚧 **Active Development — Functional desktop application and diagnostic engine**

WHYFI now includes:

- A functioning Windows diagnostic engine
- Evidence-based root-cause diagnosis
- Connection-quality analysis
- A usable command-line interface
- A native Tauri desktop application
- A React + TypeScript interface
- Real-time diagnostic progress
- Result, evidence, and recommendation screens
- Expandable technical measurements
- Development previews for failure-state testing
- **46 automated pytest tests**

The desktop application can now run the real Python diagnostic engine directly and display its results inside the native Windows interface.

WHYFI is functional in development, but it is **not yet packaged as a standalone Windows installer**.

---

## What WHYFI Can Diagnose

WHYFI currently checks:

- Windows network adapters
- Primary network connection
- Default route and gateway
- IPv4 configuration
- DHCP / APIPA issues
- Wi-Fi signal and connection information
- Gateway reachability
- Internet reachability
- DNS resolution
- Packet loss
- Latency
- Jitter
- Local vs upstream instability

Current diagnosis types:

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

WHYFI combines multiple pieces of evidence before blaming a specific part of the connection.

For example:

- Weak Wi-Fi signal alone is not enough to diagnose a Wi-Fi problem
- One noisy public endpoint is not enough to declare the internet unstable
- DNS failure is separated from general internet failure
- Local gateway instability is separated from upstream instability
- Ambiguous evidence can return `unknown` instead of forcing a weak diagnosis

---

## Desktop Application

WHYFI now has a functioning native Windows desktop application built with Tauri.

The core experience is deliberately simple:

```text
READY
  |
  v
DIAGNOSING
  |
  v
RESULT
```

The user presses one button:

> **Diagnose**

WHYFI then runs the real diagnostic engine locally and streams the current investigation stage into the interface.

Example progress:

```text
Checking network configuration...
Finding your active connection...
Checking your router...
Checking Wi-Fi signal...
Testing internet access...
Checking DNS...
```

When the investigation finishes, WHYFI displays:

- Diagnosis
- Confidence
- Plain-language summary
- Supporting evidence
- Recommended next action
- Expandable technical details

---

## Example Result

```text
Everything looks healthy.

Confidence: 96%

Your local connection, router, internet access, and DNS
are all responding normally.

Evidence:
  - Primary adapter: Wi-Fi.
  - Gateway reachable with 0.0% packet loss.
  - Average gateway latency: 2.5 ms.
  - Public targets reachable: 2/2.
  - DNS resolver responded successfully.
  - Wi-Fi signal: 79% (good).
  - Local IPv4 configuration: healthy.

Recommendation:
No action is needed based on the baseline checks.
```

Network measurements remain the source of truth.

---

## Technical Details

Users can optionally expand the result to inspect lower-level measurements without cluttering the main diagnosis.

Current technical sections include:

### Connection

- Adapter
- Connection type
- IPv4 address
- Gateway
- Link state
- Link speed
- MTU

### Gateway

- Reachability
- Average latency
- Packet loss
- Jitter

### Internet

- Public targets tested
- Public targets reachable
- Per-target latency
- Per-target packet loss

### DNS

- Resolver health
- Configured resolver
- Query latency
- DNS issue detection

### Wi-Fi

- Connection status
- Signal strength
- Radio type
- Channel
- Receive rate
- Transmit rate

### Local Configuration

- Configuration health
- DHCP issue detection
- Active adapters
- Usable IPv4 adapters

Identifying values such as the Wi-Fi SSID are intentionally not shown in the normal desktop technical-details view.

---

## How It Works

WHYFI investigates the connection in layers:

```text
Windows Network
      |
      v
Adapter + Route Discovery
      |
      v
Local IP / DHCP
      |
      v
Wi-Fi + Gateway
      |
      v
Internet + DNS
      |
      v
Evidence Collection
      |
      v
Diagnosis Engine
      |
      v
Cause + Confidence + Recommendation
```

The desktop application adds another layer around the engine:

```text
React Interface
      |
      v
Tauri / Rust
      |
      v
Python Diagnostic Engine
      |
      v
Windows Network Measurements
      |
      v
Structured JSON Events
      |
      v
Live Progress + Final Result
```

The Python engine streams diagnostic progress as JSON-line events.

Tauri reads those events and forwards them to the React interface in real time.

---

## Connection Quality Analysis

WHYFI can also perform deeper connection-quality testing using repeated measurements.

This helps distinguish:

```text
Computer <-> Router instability
            =
Local network problem
```

from:

```text
Router stable + multiple public targets unstable
            =
Likely upstream / ISP problem
```

WHYFI measures:

- Packet loss
- Minimum latency
- Average latency
- Maximum latency
- Jitter
- Stability across multiple public targets

---

## CLI

WHYFI can also run directly from the terminal.

Install in development mode:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Run the standard diagnosis:

```powershell
whyfi
```

Run deeper packet-loss and jitter analysis:

```powershell
whyfi --quality
```

Show raw technical measurements:

```powershell
whyfi --details
```

Return a machine-readable result:

```powershell
whyfi --json
```

Stream machine-readable progress and result events:

```powershell
whyfi --stream-json
```

View available commands:

```powershell
whyfi --help
```

---

## Streaming Diagnostic Protocol

The desktop application uses WHYFI's streaming JSON interface.

Example:

```json
{"type":"progress","message":"Checking network configuration..."}
{"type":"progress","message":"Finding your active connection..."}
{"type":"progress","message":"Checking your router..."}
{"type":"progress","message":"Checking Wi-Fi signal..."}
{"type":"progress","message":"Testing internet access..."}
{"type":"progress","message":"Checking DNS..."}
{"type":"result","diagnosis":{"code":"healthy","confidence":96}}
```

This allows the desktop interface to display real backend progress instead of simulated loading messages.

---

## Development Result Previews

The development build includes preview controls for testing result screens without intentionally breaking the network.

Previewable states include:

```text
no_connection
local_config_issue
gateway_issue
internet_issue
dns_issue
wifi_issue
unstable_connection
unknown
```

These controls are development-only and are excluded from production builds.

They are used to validate:

- Long diagnosis titles
- Low-confidence results
- Problem-state colors
- Evidence layout
- Recommendations
- Unknown / ambiguous diagnoses
- Different failure scenarios

---

## Testing

WHYFI currently has **46 automated pytest tests**.

Current result:

```text
46 passed
```

Run the full suite with:

```powershell
pytest -v
```

Coverage includes:

- Healthy connection
- No primary connection
- DHCP / APIPA failure
- Gateway failure
- Upstream internet failure
- DNS failure
- Weak Wi-Fi with supporting packet loss
- Gateway jitter
- Public jitter
- Packet loss
- Single noisy public-target protection
- Local vs upstream instability
- CLI behavior
- Machine-readable JSON output
- Streaming JSON output
- Diagnostic progress reporting
- Conservative diagnosis rules

---

## Technology

### Diagnostic Engine

- Python 3.12
- `psutil`
- `dnspython`
- Windows networking utilities
- Windows `ping`
- Windows `netsh`
- pytest

### Desktop Application

- Tauri 2
- Rust
- React 19
- TypeScript
- Vite
- Windows WebView
- Custom CSS

### Development

- Git
- GitHub
- Node.js
- npm
- Cargo
- Visual Studio Build Tools
- Windows SDK

---

## Run the Desktop App

From the `desktop` directory:

```powershell
npm install
npm run tauri dev
```

The current development build expects the WHYFI Python environment to exist in the project-level `.venv`.

Windows development also requires the Visual Studio C++ build tools and Windows SDK used by Tauri and Rust.

A standalone installer that bundles everything required to run WHYFI is planned for V1.0.

---

## Roadmap

### V0.1 — Diagnostic Core

**Status: Core functionality implemented**

- [x] Adapter and route discovery
- [x] Primary connection detection
- [x] Gateway diagnostics
- [x] Internet reachability
- [x] DNS diagnostics
- [x] Wi-Fi diagnostics
- [x] IPv4 / DHCP diagnostics
- [x] Latency and packet-loss measurement
- [x] Jitter measurement
- [x] Deeper connection-quality sampling
- [x] Local vs upstream instability detection
- [ ] Additional Windows networking edge cases
- [ ] More resilient Windows command parsing

### V0.2 — Diagnosis Engine

**Status: Core functionality implemented / expanding**

- [x] Evidence-based diagnosis rules
- [x] Confidence scoring
- [x] Root-cause classifications
- [x] Connection-quality diagnosis
- [x] Conservative multi-signal reasoning
- [x] Automated scenario coverage
- [ ] Additional edge cases
- [ ] Broader evidence scoring
- [ ] Confidence calibration

### V0.3 — Usable Local Application

**Status: Complete**

- [x] CLI entry point
- [x] Installed `whyfi` command
- [x] Single-command diagnosis
- [x] Deeper quality mode
- [x] Technical-details mode
- [x] Live diagnostic progress
- [x] JSON output
- [x] Streaming JSON protocol
- [x] Automated CLI coverage

### V0.4 — Desktop Application

**Status: Mostly implemented**

- [x] Tauri application shell
- [x] Rust backend bridge
- [x] React + TypeScript frontend
- [x] WHYFI-branded interface
- [x] Native Windows development build
- [x] Ready → Diagnosing → Result flow
- [x] Connect desktop app to Python diagnostic engine
- [x] Real-time diagnostic progress
- [x] Result screen
- [x] Evidence and recommendation display
- [x] Technical-details view
- [x] Healthy / problem / unknown result styling
- [x] Development result-state previews
- [ ] Additional UI polish
- [ ] Broader real-world failure testing
- [ ] Production-safe engine packaging

### V0.5 — Intelligent Investigation

**Status: Planned**

- [ ] Allowlisted diagnostic tools
- [ ] Dynamic follow-up investigation
- [ ] Privacy sanitization
- [ ] Structured AI responses
- [ ] Human-friendly explanations
- [ ] Deterministic evidence remains the source of truth

### V1.0

- [ ] Standalone Windows installer
- [ ] Bundle / package diagnostic engine
- [ ] Stable production engine bridge
- [ ] Broader Windows compatibility testing
- [ ] CI pipeline
- [ ] GitHub release
- [ ] Documentation cleanup
- [ ] Screenshots
- [ ] Demo video

---

## Design Philosophy

WHYFI should be simple on the outside and technically deep underneath.

The finished application should have:

- No account
- No login
- No cloud dashboard
- No complicated controls
- No networking knowledge required
- One primary action: **Diagnose**

The goal is closer to:

> **Shazam for broken internet**

than a traditional network administration utility.

The intended experience is:

> Press Diagnose.  
> Wait a few seconds.  
> Understand what is wrong.

---

## AI Direction

AI is intentionally **not** the foundation of WHYFI's diagnostic logic.

The deterministic engine comes first so WHYFI can continue diagnosing problems even when the internet itself is unavailable.

A later AI layer may help with:

- Ambiguous cases
- Follow-up tool selection
- Natural-language explanations
- Guided troubleshooting
- Choosing which additional safe diagnostic to run

But measurable network evidence will remain the source of truth.

---

## Next Milestone

### Finish and Harden V0.4

The desktop application now successfully performs real network investigations from the native Windows interface.

The next development phase will focus on hardening the existing desktop experience rather than adding unrelated features.

Priorities include:

```text
Real-world failure testing
        ↓
UI / result polish
        ↓
Additional engine edge cases
        ↓
Production-safe Python packaging
        ↓
Standalone Windows build
```

The immediate goal is to turn the current working development application into something that can eventually be installed and run on another Windows computer without requiring the source repository or development environment.
