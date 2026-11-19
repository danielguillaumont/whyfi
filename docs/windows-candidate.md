# Private Windows x64 candidate

Build from a clean Git checkout on native Windows x64. R03B-A targets the unsigned NSIS per-user installer `whyfi_0.1.0_x64-setup.exe`. Use a separate checkout if development builds are running. The candidate shares Tauri's standard sidecar staging directory with development builds.

## Prepare the build host

| Input | Requirement |
| --- | --- |
| Python | Windows x64 Python 3.12 in a dedicated virtual environment with the project dependencies and PyInstaller already present. The validation environment used Python 3.12.2, PyInstaller 6.22.3, psutil 7.2.2, and dnspython 2.8.0. |
| Frontend | Windows x64 Node 22 and npm. Provision `desktop/node_modules` with `npm ci` from the checked-in lockfile. The validation host used Node 22.15.0 and npm 10.9.2. |
| Rust | Native `x86_64-pc-windows-msvc` Rust with MSVC C++ Build Tools and a Windows SDK. The validation host used Rust 1.98.1. Prepopulate the Cargo cache for `Cargo.lock`. Candidate compilation uses Cargo locked and offline. |
| Bundler | The npm lockfile selects Tauri CLI 2.11.4. Its complete NSIS 3.11 cache, with the matching Tauri NSIS utilities 0.5.3 plugin, must be under `%LOCALAPPDATA%\tauri\NSIS`. The upstream bundler source documents the archives and their expected checksums. Provision the cache separately with approval. |

Keep the Python environment scoped to build dependencies. The candidate record captures resolved package versions, including transitive dependencies and PyInstaller hooks, with `pip list --format=json`. To repeat a build, provision a fresh environment with those versions and the same Python patch version. Retain verified Windows x64 wheels if offline reproduction is needed. Versions and hashes support traceability. Bit-for-bit reproduction has not been established.

See the [pinned Tauri NSIS bundler source](https://github.com/tauri-apps/tauri/blob/tauri-cli-v2.11.4/crates/tauri-bundler/src/bundle/windows/nsis/mod.rs) for cache files and checksums. The candidate command does not install dependencies.

## Build and inspect

Run from the repository root using the prepared Python environment.

```powershell
.\.venv\Scripts\python.exe scripts/build_candidate.py --preflight
.\.venv\Scripts\python.exe scripts/build_candidate.py
```

Preflight checks the host, application versions, local tools, and NSIS cache completeness. The build requires a clean checkout and puts frontend and Cargo output in a new ignored `build/candidates/<commit>-<suffix>/` directory. PyInstaller builds the target-suffixed sidecar in fresh scratch space, then validates and publishes it to Tauri's standard staging path. The candidate uses only NSIS and retains the existing app identifier, product name, icons, and security configuration. The installer is per-user and uses WebView2's download bootstrapper when the runtime is missing. That installation path requires internet access.

Use only candidate directories containing a completed `candidate.json` and `SHA256SUMS`. The candidate forces Vite production mode and `NODE_ENV=production` even in a development shell. The manifest records both frontend settings, the commit, package version, dependency and tool versions, lockfile hashes, artifact paths, hashes, PE machines, and observed Authenticode status. The app and engine must both be x64. The NSIS launcher itself may be x86. The generated NSIS script must name the same verified sidecar for installation as `whyfi-engine.exe`, and Tauri's adjacent sidecar copy must match its hash. A failed build leaves no completed candidate record. Do not substitute old outputs from the default Tauri target directory.

## Acceptance

Current installer creation and clean-machine installation remain unverified until the NSIS cache is provisioned and the exact new artifact passes these checks. Historical installer results do not apply to this candidate.

Transfer the exact installer and manifest privately. On an authorized clean Windows x64 profile with no development tools, verify the installer hash, run setup as a standard user, launch from the installed shortcut, and confirm the installed engine matches the manifest and sits beside WHYFI. Test a real diagnosis, cancel during progress and near completion, retry, short timeout, application exit, and uninstall. Observe the direct child and descendants separately. Record WebView2 behavior with and without an existing runtime. Complete the [Windows accessibility checklist](design/r02eb-windows-checklist.md).

A GitHub Actions upload is deferred. The repository is public, and repository readers can download workflow artifacts. A private distribution location is required before automating artifact sharing.
