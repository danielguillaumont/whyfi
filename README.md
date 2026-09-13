# WHYFI

> Find out why your internet isn't working.

WHYFI is an intelligent network diagnostic agent for Windows that investigates connectivity problems, identifies the most likely failure point, and explains what is happening in plain language.

The goal is simple:

**One click → investigate → diagnose → explain.**

---

## What is WHYFI?

Traditional network troubleshooting requires users to understand tools such as `ping`, `ipconfig`, `tracert`, DNS resolvers, gateways, packet loss, and Wi-Fi signal strength.

WHYFI performs those investigations automatically.

Instead of presenting raw networking data, WHYFI gathers evidence across the connection path and answers the question users actually care about:

> Why isn't my internet working?

Example:

**Your Wi-Fi is fine. Your DNS isn't.**

- Gateway latency: 3 ms ✓
- Internet latency: 18 ms ✓
- Default DNS: failed ✕
- Alternate DNS: 21 ms ✓
- Packet loss: 0% ✓

WHYFI then explains the likely cause and recommends the next action.

---

## Design Philosophy

WHYFI is intentionally simple on the outside and technically sophisticated underneath.

The application will have:

- No account
- No login
- No dashboard
- No cloud database
- No chatbot interface
- One primary action: **Diagnose**

Network measurements and deterministic evidence drive the diagnosis.

AI is used selectively for investigation, tool selection, and human-friendly explanations rather than replacing the underlying diagnostic logic.

---

## Planned V1 Diagnoses

WHYFI V1 will identify:

1. Healthy connection
2. Disconnected network adapter
3. Local network configuration problem
4. Router / default gateway problem
5. Wi-Fi quality problem
6. DNS problem
7. ISP / upstream connectivity problem
8. Unstable connection / packet loss

---

## Planned Architecture

```text
User
 │
 ▼
WHYFI Desktop Application
 │
 ▼
Baseline Health Check
 │
 ├── Adapter
 ├── Gateway
 ├── Internet
 └── DNS
 │
 ▼
Evidence Engine
 │
 ▼
Diagnosis Engine
 │
 ├── Healthy
 ├── Local network issue
 ├── Gateway issue
 ├── Wi-Fi issue
 ├── DNS issue
 └── ISP issue
 │
 ▼
Optional AI Investigation
 │
 ▼
Human-Friendly Explanation
```

---

## Technology

### Desktop

- Tauri
- React
- TypeScript
- Vite
- Tailwind CSS

### Diagnostic Engine

- Python
- Pydantic
- psutil
- dnspython
- HTTPX
- Windows networking utilities and APIs

### AI

- Tool-based diagnostic investigation
- Structured outputs
- Evidence-backed explanations
- Constrained diagnostic tools

### Engineering

- pytest
- GitHub Actions
- Git
- Automated diagnostic scenario testing

---

## Repository Structure

```text
whyfi/
│
├── desktop/                 # Tauri + React desktop application
│
├── engine/
│   ├── whyfi/
│   │   ├── diagnostics/     # Network measurement tools
│   │   ├── evidence/        # Evidence extraction
│   │   ├── diagnosis/       # Root-cause scoring
│   │   ├── agent/           # AI investigation layer
│   │   ├── privacy/         # Data sanitization
│   │   └── models/          # Shared structured models
│   │
│   └── tests/               # Unit and scenario tests
│
├── docs/
│   ├── architecture/
│   └── screenshots/
│
└── .github/
    └── workflows/
```

---

## Project Status

🚧 **Early Development**

Current phase:

**Phase 1 — Project initialization**

Next:

**Phase 2 — Local Python diagnostic engine**

The first working prototype will run entirely from the command line before the desktop interface is introduced.

---

## Roadmap

### V0.1 — Diagnostic Engine

- Detect active network adapters
- Identify default gateway
- Test gateway connectivity
- Test raw internet connectivity
- Inspect configured DNS
- Test DNS resolution
- Measure latency and packet loss

### V0.2 — Diagnosis Engine

- Structured evidence model
- Root-cause scoring
- Confidence scoring
- Simulated failure scenarios
- Automated evaluation suite

### V0.3 — Desktop Application

- Tauri shell
- React interface
- Live diagnostic progress
- Diagnosis results
- Technical details view

### V0.4 — Intelligent Investigation

- AI diagnostic tools
- Dynamic investigation
- Privacy sanitization
- Human-friendly explanations

### V1.0

- Windows installer
- Stable diagnostic engine
- Automated test suite
- GitHub release
- Demo video
- Documentation

---

## Future Ideas

Potential post-V1 features include:

- Jitter analysis
- Bufferbloat detection
- Loaded latency testing
- Speed testing
- VPN detection
- TLS diagnostics
- IPv6 diagnostics
- Captive portal detection
- MTU problems
- Advanced traceroute analysis
- macOS support
- Linux support

---

## Project Goal

WHYFI is being built as both a practical networking utility and an exploration of how deterministic systems diagnostics can be combined with constrained AI agents.

The objective is not to build an AI wrapper around networking commands.

The objective is to build a reliable diagnostic system first—and then use AI where it provides genuine value.