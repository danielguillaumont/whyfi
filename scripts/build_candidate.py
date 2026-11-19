"""Build a private, unsigned WHYFI Windows x64 NSIS candidate from local tools."""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from tempfile import mkdtemp

from build_sidecar import (
    AMD64, ROOT, SIDECAR, TARGET, build_sidecar, command_output, file_digest,
    pe_machine, require_native_x64, source_state,
)


DESKTOP = ROOT / "desktop"
TAURI = DESKTOP / "src-tauri"
MODULES = DESKTOP / "node_modules"
CLI = MODULES / "@tauri-apps" / "cli" / "tauri.js"
TAURI_CLI_VERSION = "2.11.4"
PLUGIN = "Plugins/x86-unicode/additional/nsis_tauri_utils.dll"
PLUGIN_SHA1 = "75197fee3c6a814fe035788d1c34ead39349b860"
# Cache completeness checks from the pinned Tauri CLI bundler.
NSIS_FILES = (
    "makensis.exe", "Bin/makensis.exe", "Stubs/lzma-x86-unicode",
    "Stubs/lzma_solid-x86-unicode", PLUGIN, "Include/MUI2.nsh",
    "Include/FileFunc.nsh", "Include/x64.nsh", "Include/nsDialogs.nsh",
    "Include/WinMessages.nsh", "Include/Win/COM.nsh", "Include/Win/Propkey.nsh",
    "Include/Win/RestartManager.nsh",
)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def require_nsis(cache: Path) -> None:
    missing = [name for name in NSIS_FILES if not (cache / name).is_file()]
    if missing:
        raise RuntimeError(
            f"Tauri NSIS cache incomplete at {cache}. Missing {', '.join(missing)}. "
            "Provision the approved NSIS 3.11 cache and Tauri NSIS utilities 0.5.3 before retrying."
        )
    if file_digest(cache / PLUGIN, "sha1") != PLUGIN_SHA1:
        raise RuntimeError(f"Tauri NSIS utilities hash mismatch at {cache / PLUGIN}.")


def release_version() -> str:
    config = read_json(TAURI / "tauri.conf.json")
    version = config["version"]
    versions = (
        tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"],
        tomllib.loads((TAURI / "Cargo.toml").read_text(encoding="utf-8"))["package"]["version"],
        read_json(DESKTOP / "package.json")["version"],
        read_json(DESKTOP / "package-lock.json")["packages"][""]["version"],
    )
    if not re.fullmatch(r"\d+\.\d+\.\d+", version) or any(item != version for item in versions):
        raise RuntimeError("Tauri, Python, Cargo and npm application versions must agree.")
    if config["productName"] != "whyfi" or config["identifier"] != "com.whyfi.desktop":
        raise RuntimeError("The candidate must preserve the WHYFI installer identity.")
    return version


def preflight() -> tuple[str, dict]:
    rust = require_native_x64()
    version = release_version()
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("Use the Windows x64 Python 3.12 build environment.")
    for tool in (CLI, MODULES / "typescript/bin/tsc", MODULES / "vite/bin/vite.js"):
        if not tool.is_file():
            raise RuntimeError(f"Missing {tool}. Provision desktop dependencies with npm ci first.")
    locked_cli = read_json(DESKTOP / "package-lock.json")["packages"]["node_modules/@tauri-apps/cli"]["version"]
    installed_cli = command_output("node", str(CLI), "--version", cwd=DESKTOP)
    if locked_cli != TAURI_CLI_VERSION or installed_cli != f"tauri-cli {TAURI_CLI_VERSION}":
        raise RuntimeError("Tauri CLI differs from the candidate's locked NSIS cache checks.")
    node = command_output("node", "--version")
    if not node.startswith("v22.") or command_output("node", "-p", "process.arch") != "x64":
        raise RuntimeError("Use Node 22 for Windows x64.")
    nsis = Path(os.environ["LOCALAPPDATA"]) / "tauri" / "NSIS"
    require_nsis(nsis)
    command_output(sys.executable, "-m", "pip", "check")
    tools = {
        "python": platform.python_version(),
        "python_packages": json.loads(command_output(sys.executable, "-m", "pip", "list", "--format=json")),
        "pyinstaller": command_output(sys.executable, "-m", "PyInstaller", "--version"),
        "rustc": rust,
        "cargo": command_output("cargo", "--version"),
        "node": node,
        "npm": command_output("cmd.exe", "/d", "/c", "npm.cmd --version"),
        "tauri_cli": TAURI_CLI_VERSION,
        "nsis": command_output(str(nsis / "makensis.exe"), "/VERSION"),
        "nsis_utils_sha1": PLUGIN_SHA1,
    }
    return version, tools


def artifact(path: Path, output: Path, *, x64: bool = False) -> dict:
    machine = pe_machine(path)
    if x64 and machine != AMD64:
        raise RuntimeError(f"Expected x64 payload: {path}")
    # Pass the filename as data, including for working paths containing spaces.
    env = {**os.environ, "WHYFI_CANDIDATE_SIGNATURE_PATH": str(path)}
    signature = subprocess.check_output([
        "powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
        "(Get-AuthenticodeSignature -LiteralPath $env:WHYFI_CANDIDATE_SIGNATURE_PATH).Status.ToString()",
    ], env=env, text=True).strip()
    if signature != "NotSigned":
        raise RuntimeError(f"Expected an unsigned private candidate, got {signature}: {path}")
    return {
        "path": path.relative_to(output).as_posix(),
        "sha256": file_digest(path),
        "pe_machine": "x64" if machine == AMD64 else "x86",
        "signing": signature,
    }


def verify_installer_input(script: Path, sidecar: Path) -> None:
    directive = re.search(
        r'^\s*File /a "/oname=whyfi-engine\.exe" "([^"\r\n]+)"\s*$',
        script.read_text(encoding="utf-8-sig"), re.MULTILINE,
    )
    if not directive or not Path(directive[1]).samefile(sidecar):
        raise RuntimeError("The generated NSIS script does not package the verified sidecar.")


def build_frontend(output: Path) -> None:
    env = {**os.environ, "NODE_ENV": "production"}
    subprocess.run(
        ["node", str(MODULES / "typescript/bin/tsc"), "--noEmit"],
        cwd=DESKTOP, env=env, check=True,
    )
    subprocess.run([
        "node", str(MODULES / "vite/bin/vite.js"), "build", "--mode", "production",
        "--outDir", str(output),
    ], cwd=DESKTOP, env=env, check=True)


def build_candidate(version: str, tools: dict) -> Path:
    source = source_state()
    if source["dirty"]:
        raise RuntimeError("Use a clean Git checkout so the candidate can be traced to its commit.")
    candidate_root = ROOT / "build" / "candidates"
    candidate_root.mkdir(parents=True, exist_ok=True)
    output = Path(mkdtemp(prefix=f"{source['commit'][:12]}-", dir=candidate_root))
    # Isolate Cargo and Vite outputs. Only the standard Tauri sidecar staging
    # path is shared with the development build.
    env = {
        **os.environ, "CARGO_TARGET_DIR": str(output / "cargo"), "CARGO_NET_OFFLINE": "true",
    }
    for key in ("TAURI_CONFIG", "CARGO_BUILD_TARGET"):
        env.pop(key, None)
    build_frontend(output / "frontend")
    sidecar = build_sidecar()
    staged = Path(sidecar["path"])
    override = output / "tauri.candidate.json"
    override.write_text(json.dumps({
        "build": {"beforeBuildCommand": None, "frontendDist": str(output / "frontend")},
        "bundle": {"targets": ["nsis"], "windows": {
            "webviewInstallMode": {"type": "downloadBootstrapper"},
            "nsis": {"installMode": "currentUser"},
        }},
    }), encoding="utf-8")
    subprocess.run([
        "node", str(CLI), "build", "--config", str(override), "--target", TARGET,
        "--bundles", "nsis", "--ci", "--no-sign", "--", "--locked", "--offline",
    ], cwd=DESKTOP, env=env, check=True)
    release = output / "cargo" / TARGET / "release"
    app = release / "whyfi.exe"
    payload = release / "whyfi-engine.exe"
    installer = release / "bundle" / "nsis" / f"whyfi_{version}_x64-setup.exe"
    verify_installer_input(release / "nsis" / "x64" / "installer.nsi", staged)
    if file_digest(payload) != sidecar["sha256"] or file_digest(staged) != sidecar["sha256"]:
        raise RuntimeError("The sidecar bytes changed between staging and bundling.")
    artifacts = {
        "installer": artifact(installer, output),
        "desktop": artifact(app, output, x64=True),
        "sidecar": artifact(payload, output, x64=True),
    }
    if source_state() != source or sidecar["commit"] != source["commit"] or sidecar["dirty"]:
        raise RuntimeError("Git source state changed during the candidate build.")
    (output / "SHA256SUMS").write_text(
        "".join(f"{item['sha256']}  {item['path']}\n" for item in artifacts.values()), encoding="utf-8",
    )
    (output / "candidate.json").write_text(json.dumps({
        "source": source, "version": version, "target": TARGET, "tools": tools, "artifacts": artifacts,
        "frontend": {"mode": "production", "node_env": "production"},
        "lockfiles": {
            path: file_digest(ROOT / path)
            for path in ("desktop/package-lock.json", "desktop/src-tauri/Cargo.lock")
        },
    }, indent=2) + "\n", encoding="utf-8")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true", help="Check local prerequisites without building.")
    args = parser.parse_args()
    try:
        version, tools = preflight()
        if args.preflight:
            print(json.dumps({"version": version, "target": TARGET, "tools": tools}, indent=2))
        else:
            print(f"Candidate ready: {build_candidate(version, tools)}")
    except (OSError, RuntimeError, subprocess.CalledProcessError, KeyError, ValueError) as error:
        sys.exit(f"Candidate build failed: {error}")
