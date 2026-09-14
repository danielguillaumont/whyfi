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
- **46 automated pytest tests**

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

The diagnostic engine streams newline-delimited JSON events.

Example:

```json
{"type":"progress","message":"Checking your router..."}
{"type":"progress","message":"Testing internet access..."}
{"type":"result","diagnosis":{"code":"healthy","confidence":96}}
```

Tauri receives these events from the bundled engine and forwards them to the React interface.

The deterministic network engine remains the source of truth.

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

---

## Testing

WHYFI currently has:

```text
46 passed
```

Run the suite with:

```powershell
pytest -q
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
- [ ] CI pipeline
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
