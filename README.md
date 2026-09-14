# WHYFI

> Find out why your internet is acting weird.

WHYFI is a Windows network diagnostic tool that investigates connectivity problems, identifies the most likely failure point, and explains what is happening in plain language.

Instead of asking users to understand DNS, DHCP, gateways, routing, packet loss, or jitter, WHYFI collects the evidence automatically and answers:

> **Why isn't my internet working properly?**

---

## Current Status

🚧 **Active Development — Diagnostic engine, CLI, and desktop shell are working**

WHYFI currently includes:

- A functioning Windows diagnostic engine
- Evidence-based root-cause diagnosis
- Deeper connection-quality testing
- A usable command-line interface
- A native Tauri desktop application shell
- A WHYFI-branded React desktop interface
- 44 automated tests

The desktop interface is currently being connected to the existing Python diagnostic engine.

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

WHYFI deliberately combines multiple pieces of evidence before blaming a specific part of the connection.

For example, weak Wi-Fi signal alone is not enough to diagnose a Wi-Fi problem, and one noisy public server is not enough to declare the internet connection unstable.

---

## Example Diagnosis

```text
WHYFI
==================================================
Investigating your network...
Checking network configuration...
Finding your active connection...
Checking your router...
Checking Wi-Fi signal...
Testing internet access...
Checking DNS...

Everything looks healthy.
Confidence: 96%

Your local connection, router, internet access, and DNS
are all responding normally.

Evidence:
  - Primary adapter: Wi-Fi.
  - Gateway reachable with 0.0% packet loss.
  - Public targets reachable: 2/2.
  - Wi-Fi signal: 79% (good).
  - Local IPv4 configuration: healthy.

Recommendation:
No action is needed based on the baseline checks.
```

Network measurements remain the source of truth.

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

A deeper quality investigation also takes multiple samples from the gateway and independent public targets.

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

---

## CLI

Install WHYFI in development mode:

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

View available commands:

```powershell
whyfi --help
```

---

## Desktop Application

WHYFI now has a working Tauri + React desktop shell.

The first interface is running locally with the intended simple product direction:

> **What's wrong with my internet?**

The desktop experience is being designed around three main states:

```text
READY
  |
  v
DIAGNOSING
  |
  v
RESULT
```

The next step is connecting the **Diagnose** button to the existing Python diagnostic engine.

### Run the Desktop App

From the `desktop` directory:

```powershell
npm install
npm run tauri dev
```

Windows development requires the Visual Studio C++ build tools and Windows SDK required by Tauri/Rust.

---

## Testing

WHYFI currently has **44 automated pytest tests**.

Current result:

```text
44 passed
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
- CLI modes
- Diagnostic progress reporting

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
- Visual Studio Build Tools
- Node.js / npm

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
- [x] Automated CLI coverage

### V0.4 — Desktop Application

**Status: In progress**

- [x] Tauri application shell
- [x] React + TypeScript frontend
- [x] WHYFI-branded initial interface
- [x] Native Windows development build
- [ ] Ready → Diagnosing → Result flow
- [ ] Connect desktop app to Python diagnostic engine
- [ ] Live diagnostic progress
- [ ] Result screen
- [ ] Technical-details view

### V0.5 — Intelligent Investigation

**Status: Planned**

- [ ] Allowlisted diagnostic tools
- [ ] Dynamic follow-up investigation
- [ ] Privacy sanitization
- [ ] Structured AI responses
- [ ] Human-friendly explanations
- [ ] Deterministic evidence remains the source of truth

### V1.0

- [ ] Windows installer
- [ ] Stable diagnostic engine
- [ ] CI pipeline
- [ ] GitHub release
- [ ] Documentation
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

The goal is closer to **Shazam for broken internet** than a traditional network administration tool.

> Press Diagnose.  
> Wait a few seconds.  
> Understand what is wrong.

---

## AI Direction

AI is intentionally **not** the foundation of WHYFI's diagnostic logic.

The deterministic engine is being built first so the application can still diagnose problems when the internet itself is unavailable.

A later AI layer may help with:

- Ambiguous cases
- Follow-up tool selection
- Natural-language explanations
- Guided troubleshooting

But measurable network evidence will remain the source of truth.

---

## Next Milestone

### Connect the Desktop App to the Diagnostic Engine

The Tauri + React application shell and first WHYFI interface are now running.

The next step is turning the **Diagnose** button into a real investigation:

```text
Ready
  ↓
Diagnosing
  ↓
Result
```

That result will come from the same deterministic Python engine already used by the CLI and will display:

- Diagnosis
- Confidence
- Evidence
- Recommendation
- Technical details