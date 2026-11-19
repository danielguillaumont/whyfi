# WHYFI architecture

```
React / TypeScript workspace (WebView2)
  -> Tauri IPC (start and cancel)
    -> Rust investigation supervisor
      -> Python diagnostic sidecar
        -> Windows networking APIs, PowerShell and netsh, DNS and ICMP probes

Windows evidence -> Python diagnosis -> validated NDJSON -> Rust outcome -> React
```

| Layer | Ownership |
| --- | --- |
| [React workspace](../desktop/src/App.tsx) and [investigation hook](../desktop/src/useInvestigation.ts) | Start and cancel through Tauri, ignore stale run events, and render conclusions and technical evidence. |
| [Tauri commands](../desktop/src-tauri/src/lib.rs) and [main-window capability](../desktop/src-tauri/capabilities/default.json) | Expose start and cancel to the local main window. The Rust shell plugin resolves the fixed bundled `whyfi-engine` executable and the bridge passes `--stream-json`. |
| [Rust supervisor](../desktop/src-tauri/src/investigation.rs) and [stream validation](../desktop/src-tauri/src/sidecar_protocol.rs) | Enforce one active run, match cancellation to its run ID, limit investigation duration, and require a valid terminal outcome. Validate NDJSON across byte chunks, cap a record at 1 MiB, and retain at most 8 KiB of stderr. |
| [Python baseline](../engine/whyfi/diagnostics/windows/baseline.py) and [diagnosis rules](../engine/whyfi/diagnosis/engine.py) | Collect Windows evidence, distinguish unavailable from negative observations, and produce a rule-based conclusion and recommendation. [Windows DNS attribution](../engine/whyfi/diagnostics/windows/dns.py) keeps system lookup, direct queries, and resolver inventory separate. |

## Run lifecycle

`start_diagnosis` reserves the active slot, sends the run ID and progress through a per-invocation channel, and returns a terminal outcome for that same ID. `cancel_diagnosis` accepts only the matching active ID. An accepted cancellation wins if the worker has not yet claimed the terminal outcome.

The default deadline is **120 seconds**, including startup and a three-second cleanup reserve. Set `WHYFI_INVESTIGATION_TIMEOUT_SECONDS` in the desktop process environment before launch to override it. Accepted values are whole seconds from 5 to 600.

Rust observes direct-child exit separately from stdout and stderr. Cancellation, timeout, and protocol failure request direct-child termination. The slot stays reserved while exit remains unconfirmed, even if the user has already received an outcome. Windows helpers spawned by the packaged engine can outlive the direct child. The supervisor does not terminate the entire process tree.

## WebView and packaging boundaries

The [production CSP](../desktop/src-tauri/tauri.conf.json) denies resources by default, allows bundled scripts, styles, and images, and limits connections to local Tauri IPC. The main window can invoke the two investigation commands. It has no generic shell or filesystem permission. The native app and sidecar run with the Windows user's privileges.

The [sidecar build](../scripts/build_sidecar.py) generates a fresh PyInstaller executable for the Windows x64 target. The [candidate build](../scripts/build_candidate.py) uses isolated frontend and Cargo outputs, packages through NSIS, and checks the app and sidecar architecture, installer inputs, hashes, and Authenticode status. Installed application behavior is a separate acceptance step.
