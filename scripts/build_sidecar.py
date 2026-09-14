from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ENGINE_ENTRY = ROOT / "engine" / "whyfi" / "__main__.py"
ENGINE_PATH = ROOT / "engine"
BIN_DIR = ROOT / "desktop" / "src-tauri" / "binaries"
BUILD_DIR = ROOT / "build" / "pyinstaller"


def get_rust_target() -> str:
    result = subprocess.run(
        ["rustc", "-vV"],
        check=True,
        capture_output=True,
        text=True,
    )

    for line in result.stdout.splitlines():
        if line.startswith("host: "):
            return line.removeprefix("host: ").strip()

    raise RuntimeError("Could not determine the Rust target triple.")


def main() -> None:
    target = get_rust_target()

    if not target.endswith("windows-msvc"):
        raise RuntimeError(
            f"WHYFI sidecar packaging currently supports Windows MSVC only, got: {target}"
        )

    BIN_DIR.mkdir(parents=True, exist_ok=True)

    output_name = f"whyfi-engine-{target}"

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--clean",
        "--name",
        output_name,
        "--paths",
        str(ENGINE_PATH),
        "--distpath",
        str(BIN_DIR),
        "--workpath",
        str(BUILD_DIR),
        "--specpath",
        str(BUILD_DIR),
        str(ENGINE_ENTRY),
    ]

    print(f"Building WHYFI sidecar for {target}...")
    subprocess.run(command, cwd=ROOT, check=True)

    output_path = BIN_DIR / f"{output_name}.exe"

    if not output_path.exists():
        raise RuntimeError(
            f"Expected sidecar was not created: {output_path}"
        )

    print(f"Sidecar ready: {output_path}")


if __name__ == "__main__":
    main()
