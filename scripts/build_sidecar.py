from __future__ import annotations

import hashlib
import json
import os
import platform
import struct
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parent.parent
ENGINE_PATH = ROOT / "engine"
BIN_DIR = ROOT / "desktop" / "src-tauri" / "binaries"
BUILD_DIR = ROOT / "build" / "pyinstaller"
TARGET = "x86_64-pc-windows-msvc"
SIDECAR = f"whyfi-engine-{TARGET}.exe"
AMD64 = 0x8664
I386 = 0x014C


def command_output(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.check_output(args, cwd=cwd, text=True, encoding="utf-8").strip()


def source_state() -> dict:
    return {
        "commit": command_output("git", "rev-parse", "HEAD"),
        "dirty": bool(command_output("git", "status", "--porcelain", "--untracked-files=all")),
    }


def require_native_x64() -> str:
    machine = os.environ.get("PROCESSOR_ARCHITEW6432") or platform.machine()
    if sys.platform != "win32" or machine.upper() != "AMD64" or struct.calcsize("P") != 8:
        raise RuntimeError("Use native Windows x64 with a 64-bit Python interpreter.")
    rust = command_output("rustc", "-vV")
    if f"host: {TARGET}" not in rust.splitlines():
        raise RuntimeError(f"Expected the native Rust host {TARGET}.")
    return rust


def file_digest(path: Path, algorithm: str = "sha256") -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def pe_machine(path: Path) -> int:
    """Identify a Windows PE executable with a file-backed entry point."""
    with path.open("rb") as stream:
        size = os.fstat(stream.fileno()).st_size

        def invalid(reason: str) -> RuntimeError:
            return RuntimeError(f"Invalid Windows PE executable {path}: {reason}.")

        dos = stream.read(64)
        if len(dos) != 64 or dos[:2] != b"MZ":
            raise invalid("missing or truncated DOS header")
        offset = struct.unpack_from("<I", dos, 60)[0]
        if not 64 <= offset <= size - 24:
            raise invalid("PE header offset is outside the file")
        stream.seek(offset)
        header = stream.read(24)
        if header[:4] != b"PE\0\0":
            raise invalid("missing PE signature")
        machine, sections, _, _, _, optional_size, flags = struct.unpack_from("<HHIIIHH", header, 4)
        formats = {AMD64: (0x20B, 112), I386: (0x10B, 96)}
        if machine not in formats:
            raise invalid(f"unsupported COFF machine 0x{machine:04x}, expected x86 or x64")
        expected_magic, minimum_optional_size = formats[machine]
        if not flags & 2 or flags & 0x2000 or not 1 <= sections <= 96:
            raise invalid("expected an executable image with a valid section count")
        section_table_end = offset + 24 + optional_size + sections * 40
        if optional_size < minimum_optional_size or section_table_end > size:
            raise invalid("optional header or section table is truncated")
        optional = stream.read(optional_size)
        if struct.unpack_from("<H", optional)[0] != expected_magic:
            raise invalid("optional header format does not match COFF machine")
        entry = struct.unpack_from("<I", optional, 16)[0]
        image_size, headers_size = struct.unpack_from("<II", optional, 56)
        if not section_table_end <= headers_size <= min(size, image_size):
            raise invalid("inconsistent image and header sizes")
        if not headers_size <= entry < image_size:
            raise invalid("entry point is zero or outside the image's section data")

        executable_entry = False
        for _ in range(sections):
            section = stream.read(40)
            virtual_size, address, raw_size, raw_offset = struct.unpack_from("<IIII", section, 8)
            characteristics = struct.unpack_from("<I", section, 36)[0]
            if raw_size and not headers_size <= raw_offset <= size - raw_size:
                raise invalid("section data is outside the file")
            mapped_size = virtual_size or raw_size
            if mapped_size and not headers_size <= address <= image_size - mapped_size:
                raise invalid("section address is outside the image")
            if characteristics & 0x20000000 and address <= entry < address + min(mapped_size, raw_size):
                executable_entry = True
        if not executable_entry:
            raise invalid("entry point does not map to file-backed executable section data")
        return machine


def build_sidecar(output_dir: Path = BIN_DIR) -> dict:
    require_native_x64()
    source = source_state()
    output_dir.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    # PyInstaller must produce the expected name inside a new staging directory.
    # Publish only a validated executable and never trust an existing destination.
    with TemporaryDirectory(prefix="sidecar-", dir=BUILD_DIR) as staging:
        stage = Path(staging)
        output = stage / SIDECAR
        subprocess.run([
            sys.executable, "-m", "PyInstaller", "--onefile", "--clean",
            "--name", output.stem, "--paths", str(ENGINE_PATH),
            "--distpath", str(stage), "--workpath", str(stage / "work"),
            "--specpath", str(stage), str(ENGINE_PATH / "whyfi" / "__main__.py"),
        ], cwd=ROOT, check=True)
        if not output.is_file():
            raise RuntimeError(f"PyInstaller did not create the fresh file {SIDECAR}.")
        if pe_machine(output) != AMD64:
            raise RuntimeError(f"{SIDECAR} is not an x64 Windows executable.")
        if source_state() != source:
            raise RuntimeError("Git source state changed during the sidecar build.")
        digest = file_digest(output)
        destination = output_dir / SIDECAR
        output.replace(destination)
    return {**source, "target": TARGET, "sha256": digest, "path": str(destination)}


def main() -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    record = build_sidecar()
    (BUILD_DIR / "sidecar.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"Sidecar ready: {record['path']} (SHA-256 {record['sha256']})")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        sys.exit(f"Sidecar build failed: {error}")
