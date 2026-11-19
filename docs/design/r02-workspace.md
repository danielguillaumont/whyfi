# WHYFI R02 workspace specification

This foundation targets Windows WebView2 and the diagnostic contracts at `fd5dc5073a0e579de77f9b910fee24beb2c11492`. The workspace shell and Result overview adopt the token stylesheet. The deeper Evidence redesign remains a later slice.

## Users and workflow

- **Everyday Windows user.** Start at Diagnose, run a check, and read what happened and what to do. Keep network jargon and measurement detail behind Evidence. Cancel, retry, and recover from a timeout without losing access to the main action.
- **IT professional or support technician.** Open Evidence from a finished investigation. Compare the local gateway and public targets, inspect adapter data and DNS attribution, and distinguish a failed test from a measurement WHYFI could not collect.

## Workspace and navigation

Use one workspace with the native Windows title bar. Place the WHYFI identity and view controls in a compact shell. Use only three destinations, each backed by a real view.

| View | Content and actions | Navigation |
| --- | --- | --- |
| **Diagnose** | One primary Diagnose action, with progress and cancellation while running. Show a concise recovery message after cancellation, failure, or timeout. | Default on launch. Start and retry use the same controller. |
| **Result** | Outcome label, diagnosis, next action, and a short list of supporting observations. | Open automatically after a valid result. Offer **View evidence** and **Run again**. |
| **Evidence** | Evidence grouped by device, local network, internet targets, and DNS. Show unavailable checks and their collection errors in context. | Open from the current result. **Back to result** restores focus to **View evidence**. Keep result and evidence views above the same in-memory run. |

Result and Evidence become available once the active investigation returns a result. Starting another run replaces that result. While diagnosing, keep Cancel in view and avoid navigation that hides the active investigation. The trial workspace does not add history, settings, or inactive tabs.

### State inventory

| State | Visible behavior |
| --- | --- |
| Ready | The Diagnose button is the primary action. A short sentence sets expectations about the checks. |
| Diagnosing | Show the latest progress text and an indeterminate indicator. Enable Cancel once Rust acknowledges the run ID. During cancellation disable duplicate requests and show **Cancelling…**. If cancellation could not be requested, restore Cancel when the controller permits a retry. |
| Cancelled | Return to Diagnose with **Investigation cancelled** and a usable primary action. Show a cleanup notice if the outcome carries one. |
| Failed | Show a plain-language failure and **Try again**. Put detailed error context in a secondary disclosure when useful. |
| Timed out | Show a distinct timeout message and **Try again**. If cleanup is still pending, surface that context and let Rust enforce its existing busy guard. |
| Healthy | Present a clear **Healthy** label, the engine conclusion, and its recommended action when present. |
| Problem | Lead with the specific engine conclusion and recommendation. Pair a text label and icon with the problem color. |
| Inconclusive | Use this label for `unknown` and explain which evidence was insufficient when known. Keep the technical details available. |

A transport failure, cancellation, or timeout is an investigation outcome. A diagnosis such as `no_connection` is an engine result. Confidence is optional engine evidence and does not determine the label. If it is null, omit the value. If the recommendation is null, omit the action copy and leave real controls available.

## Components and data

| Component | Responsibility and source |
| --- | --- |
| `AppShell` | Layout, native-window-friendly navigation, active view, and focus on view changes. Reads the controller state and owns no IPC. |
| `useInvestigation` | Wrap the existing `InvestigationFlow` and Tauri channel. Use typed phases for start, acknowledgement, progress, completion, cancellation, timeout, and failure. Parse the validated result once. Retain run-ID checks, stale-event rejection, and cancellation recovery. |
| `DiagnosisScreen` | Render the ready action and outcome recovery messages. Delegate progress to `InvestigationStatus`. |
| `InvestigationStatus` | Render the latest progress message, cancellation state, and a polite announcement. No percentage is available in the current protocol. |
| `ResultOverview` | Read `diagnosis.code`, `title`, `summary`, `recommendation`, `evidence`, and nullable `confidence`. Place the outcome first, then the next action, then supporting observations. Show a few decisive findings first and keep the rest accessible in Evidence. |
| `TechnicalEvidence` | Group `details.connection` and `local_config` under Device, `wifi` and `gateway` under Local network, `internet.probes` under Internet, and `dns` under DNS. Use `collection_errors[].check`, `target`, and `message` to attach context. Keep unscoped errors visible under Collection notes. |
| Shared primitives | Use native HTML controls for buttons and disclosures, a text-and-icon status label, a metric row with explicit units, and a probe table with headers. Add a shared focus treatment and status-message pattern. |

Keep `start_diagnosis`, the `started` and `progress` channel events, `cancel_diagnosis(runId)`, and the current terminal outcome types. Only a completed outcome contains the validated JSON result. Preserve the sidecar protocol, engine decisions, and Tauri security boundary. Extend the frontend view model to display evidence already in the contract.

### Measurement presentation

- Use **Unavailable** for a null or absent measurement and include the collection reason when present. Use **Not applicable** only when context establishes it, such as Wi-Fi details for a confirmed Ethernet connection. Use **Not queried** for known skipped probes. Treat measured `false` and measured zero as valid observations.
- Show latency and jitter in milliseconds, loss and Wi-Fi signal in percent, and reported link rates in Mbps. Use per-target summaries such as mean latency, packets sent and received, and loss. `internet.targets_tested` counts completed measurements. Keep unavailable targets listed separately from that count.
- For DNS, keep the Windows DNS-client result separate from direct primary-interface queries and off-interface resolver inventory. Label cache and policy uncertainty. Preserve interface, address family, IPv6 scope, route evidence, and unknown provisioning provenance.
- `details.completed` describes coverage. Use `diagnosis.code` for the user-facing conclusion. The current payload contains aggregate values. Use labeled summaries and per-target comparisons, and reserve timelines and hop charts for actual timestamped samples or traceroute data.
- The Result overview displays confidence as a rule-based engine score out of 100. Its Device, Gateway, and Internet cards summarize separate checks. DNS sits below the path as a resolution check. Full engine findings, including detailed errors, remain available in Evidence.

## Design system

The [token stylesheet](../../desktop/src/design-tokens.css) contains the proposed dark palette, Windows font stack, spacing, boundaries, radii, and focus values. Use dark neutral surfaces and subtle layering. Reserve the blue accent for the primary action, links, and selected navigation. Use green for healthy, amber for a diagnosed problem, neutral for inconclusive, and rose for an investigation failure. Cancellation can use a neutral notice. Each status also has a readable label.

Use Segoe UI Variable with local fallbacks. Reserve monospace for addresses and other identifiers. Start with the body token for readable content, smaller text for labels, and a compact title for outcomes. Use the spacing scale consistently rather than resizing controls to fit dense panels. Use the subtle border for dividers and the stronger control border when a boundary is necessary to identify a control. Pair the focus color with a visible offset outline. Preserve focus outlines in forced colors using system colors.

Borrow consistent action placement and hierarchy from [Linear](https://linear.app/now/behind-the-latest-design-refresh), Windows-native affordances from [Fluent and Windows accessibility guidance](https://learn.microsoft.com/en-us/windows/apps/design/accessibility/accessibility-checklist), and clear separation of latency and loss from [PingPlotter](https://www.pingplotter.com/fix-your-network/getting-started/timeline-graphs/). WHYFI should use its own mark and compact visual language. Align the favicon, native icon, window title, and in-app identity when production assets are ready. Prefer flat surfaces, small radii, and meaningful separators.

## Responsive and accessibility acceptance

- At **800 × 600**, show the primary action and current state without scrolling on Ready. Keep Cancel and retry reachable when content grows. Prefer one clear vertical scroll region, with no overlapping controls.
- At a **480 × 560 CSS-pixel snapped viewport**, collapse evidence panels to one column and use a compact view header. Let technical addresses wrap without truncating their accessible text. At **320 CSS pixels** of available width, allow controls to wrap or stack without page-level horizontal scrolling.
- On keyboard-only navigation, verify a logical Tab order, clear `:focus-visible` styling, Enter/Space activation, and focus restoration on close or Back. Move focus to the new heading or next primary action on a screen change. Avoid moving focus for each progress event.
- Expose progress through a polite live region and terminal messages once. Give disclosures a meaningful label and expanded state. Verify headings, table navigation, status labels, and button names with Narrator in WebView2.
- Verify default contrast of at least 4.5:1 for normal text and 3:1 for meaningful control and focus boundaries. Check forced colors, reduced motion, and the combined effects of Windows text size and 100%, 150%, and 200% display scaling. Animations may be removed with no loss of state information.

## Implementation sequence and scope

| Slice | Deliverable and review gate |
| --- | --- |
| **1. Shell and investigation** | Adopt tokens, extract the controller, and build compact Ready, Diagnosing, Cancelled, Failed, and Timed out views. Verify start, duplicate prevention, cancel, retry, focus, and Windows sizing. |
| **2. Result and evidence** | Split summary and evidence views. Test fixtures for healthy, problem, unknown with non-null confidence, partial evidence, real zero loss, and Windows DNS attribution. |
| **3. Evidence polish** | Add per-target comparisons grounded in the existing payload and finish keyboard, Narrator, forced-colors, and packaged WebView smoke checks. Any chart must have an accessible text or table equivalent. |

**Available now:** desktop baseline investigation, cancellation, timeout, retry, result and technical measurements, plus deeper connection-quality analysis through the CLI. **Future only:** persistent history, background monitoring, traceroute, AI assistance, and visual time series. These features require product decisions and, where relevant, new data and permissions. They do not get workspace destinations during R02.

**Open decisions:** confirm the packaged mark and favicon together, and set the enforced minimum native window size after testing snapped layouts and scaling. Neither decision blocks Slice 1.
