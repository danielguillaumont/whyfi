# WHYFI

> Find out why your internet is acting weird.

WHYFI is a Windows network diagnostic tool that investigates connectivity problems, identifies the most likely failure point, and explains what is happening in plain language.

Instead of asking the user to understand DNS, DHCP, gateways, routing, packet loss, or jitter, WHYFI collects the evidence automatically and answers the useful question:

> **Why isn't my internet working properly?**

---

## Current Status

🚧 **Active Development — Diagnostic engine and CLI are working**

WHYFI currently includes a functioning Windows diagnostic engine, evidence-based diagnosis system, deeper connection-quality testing, and a usable command-line interface.

It can currently:

- Discover Windows network adapters and the primary connection
- Identify the default route and gateway
- Inspect local IPv4 and DHCP configuration
- Detect APIPA / `169.254.x.x` addressing
- Inspect Wi-Fi signal, channel, radio type, and link rate
- Measure latency, packet loss, and jitter
- Test gateway and direct internet reachability
- Compare the configured DNS resolver with public resolvers
- Distinguish local network instability from upstream instability
- Avoid false conclusions from a single noisy public endpoint
- Produce evidence-backed diagnoses, confidence scores, and recommendations
- Show live diagnostic progress
- Expose raw technical measurements when requested
- Run through the installed `whyfi` command

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

---

## Example

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

WHYFI uses deterministic evidence-based rules for its current diagnoses. Network measurements remain the source of truth.

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

A deeper quality investigation also takes multiple samples from the local gateway and independent public targets.

This allows WHYFI to distinguish between:

```text
Computer <-> Router instability
            =
Local network problem
```

and:

```text
Router stable + multiple public targets unstable
            =
Likely upstream / ISP-side problem
```

WHYFI is deliberately conservative. Weak Wi-Fi alone does not automatically mean Wi-Fi is broken, and one noisy internet endpoint is not enough to declare the connection unstable.

---

## CLI

Install WHYFI in development mode:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Run a standard diagnosis:

```powershell
whyfi
```

Run a deeper packet-loss and jitter investigation:

```powershell
whyfi --quality
```

Show the baseline diagnosis plus raw technical measurements:

```powershell
whyfi --details
```

View available commands:

```powershell
whyfi --help
```

---

## Diagnostic Areas

### Local Network

WHYFI checks:

- Active network adapters
- Primary connection
- Default gateway
- IPv4 configuration
- DHCP / APIPA issues
- Gateway reachability
- Local packet loss
- Wi-Fi signal quality

### Internet

WHYFI checks multiple independent public targets for:

- Reachability
- Packet loss
- Minimum / average / maximum latency
- Jitter
- Upstream instability

### DNS

WHYFI can:

- Detect the configured resolver
- Test DNS resolution
- Compare against alternate public resolvers
- Distinguish DNS failure from general internet failure

---

## Testing

WHYFI currently has **44 automated pytest tests** covering diagnostic rules, parsers, edge cases, failure scenarios, CLI behavior, and progress reporting.

Current result:

```text
44 passed
```

Run the suite with:

```powershell
pytest -v
```

Examples of covered scenarios include:

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

### Current

- Python 3.12
- `psutil`
- `dnspython`
- Windows networking utilities
- Windows `ping`
- Windows `netsh`
- pytest
- Git / GitHub

### Desktop Application

Planned for the next phase:

- Tauri
- React
- TypeScript
- Vite
- Tailwind CSS

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

**Status: Next**

- [ ] Tauri application shell
- [ ] React interface
- [ ] One-click Diagnose flow
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

WHYFI is meant to be simple on the outside and technically deep underneath.

The eventual desktop application should have:

- No account
- No login
- No cloud database
- No complicated dashboard
- No chatbot required
- One primary action: **Diagnose**

The experience should feel closer to **Shazam for broken internet** than a traditional network administration utility.

The user should not need to understand the networking stack.

WHYFI should investigate it for them.

---

## AI Direction

AI is intentionally **not** the foundation of WHYFI's diagnostic logic.

The deterministic engine is being built first so that WHYFI can continue diagnosing problems even when the internet itself is unavailable.

A later AI layer may help with:

- Ambiguous cases
- Follow-up tool selection
- More natural explanations
- Guided troubleshooting

But measurable network evidence will remain the source of truth.

---

## Next Milestone

**V0.4 — Desktop Application**

The next phase is wrapping the working diagnostic engine in a lightweight Tauri + React interface with one central action:

> **Diagnose**

The goal is simple:

> Press Diagnose.  
> Wait a few seconds.  
> Understand what is wrong.