import os
import shutil
import struct
from pathlib import Path

import pytest


@pytest.fixture
def packaging(monkeypatch):
    scripts = Path(__file__).resolve().parents[2] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    from build_candidate import require_nsis, verify_installer_input
    import build_sidecar

    return build_sidecar, require_nsis, verify_installer_input


def executable(machine=0x8664):
    """Minimal PE image with one mapped .text section and a return instruction."""
    dos = bytearray(64)
    dos[:2] = b"MZ"
    struct.pack_into("<I", dos, 60, 64)
    x64 = machine == 0x8664
    optional = bytearray(240 if x64 else 224)
    struct.pack_into("<H", optional, 0, 0x20B if x64 else 0x10B)
    struct.pack_into("<I", optional, 4, 512)  # SizeOfCode
    struct.pack_into("<II", optional, 16, 0x1000, 0x1000)  # Entry and base of code
    struct.pack_into("<Q" if x64 else "<I", optional, 24 if x64 else 28, 0x400000)
    struct.pack_into("<II", optional, 32, 0x1000, 512)
    struct.pack_into("<H", optional, 40, 6)
    struct.pack_into("<H", optional, 48, 6)
    struct.pack_into("<II", optional, 56, 0x2000, 512)
    struct.pack_into("<H", optional, 68, 3)  # Console subsystem
    struct.pack_into("<I", optional, 108 if x64 else 92, 16)
    code = b"\x31\xc0\xc3"  # xor eax, eax; ret
    header = b"PE\0\0" + struct.pack("<HHIIIHH", machine, 1, 0, 0, 0, len(optional), 2)
    section = struct.pack("<8sIIIIIIHHI", b".text", len(code), 0x1000, 512, 512, 0, 0, 0, 0, 0x60000020)
    return (dos + header + optional + section).ljust(512, b"\0") + code.ljust(512, b"\0")


def test_pe_validation_accepts_file_backed_x64_and_x86_images(packaging, tmp_path):
    builder, _, _ = packaging
    image = tmp_path / "app.exe"
    for machine in (builder.AMD64, builder.I386):
        image.write_bytes(executable(machine))
        assert builder.pe_machine(image) == machine


@pytest.mark.skipif(os.name != "nt", reason="requires a Windows system executable")
def test_pe_validation_accepts_native_windows_executable(packaging):
    builder, _, _ = packaging
    cmd = Path(os.environ["SystemRoot"]) / "System32" / "cmd.exe"
    if os.environ.get("PROCESSOR_ARCHITECTURE", "").upper() != "AMD64":
        pytest.skip("requires native Windows x64")
    assert builder.pe_machine(cmd) == builder.AMD64


@pytest.mark.parametrize(("case", "reason"), [
    ("header_only", "header sizes"),
    ("truncated_table", "section table is truncated"),
    ("wrong_optional_magic", "does not match COFF machine"),
    ("wrong_architecture", "unsupported COFF machine"),
    ("outside_raw_data", "section data is outside"),
    ("zero_entry", "entry point is zero"),
    ("no_execute", "file-backed executable"),
    ("virtual_only_entry", "file-backed executable"),
])
def test_pe_validation_rejects_invalid_executables(packaging, tmp_path, case, reason):
    builder, _, _ = packaging
    image = bytearray(executable())
    optional = 88
    section = optional + 240
    if case == "header_only":
        image = image[:240]
        struct.pack_into("<H", image, 84, 112)
        image[optional + 2:] = bytes(len(image) - optional - 2)
    elif case == "truncated_table":
        image = image[:section + 39]
    elif case == "wrong_optional_magic":
        struct.pack_into("<H", image, optional, 0x10B)
    elif case == "wrong_architecture":
        struct.pack_into("<H", image, 68, 0xAA64)
    elif case == "outside_raw_data":
        struct.pack_into("<I", image, section + 20, len(image))
    elif case == "zero_entry":
        struct.pack_into("<I", image, optional + 16, 0)
    elif case == "no_execute":
        struct.pack_into("<I", image, section + 36, 0x40000020)
    else:
        struct.pack_into("<I", image, optional + 16, 0x1200)
        struct.pack_into("<I", image, section + 8, 513)
    path = tmp_path / "invalid.exe"
    path.write_bytes(image)
    with pytest.raises(RuntimeError, match=reason):
        builder.pe_machine(path)


def test_candidate_frontend_output_ignores_development_parent(packaging, tmp_path, monkeypatch):
    import build_candidate as candidate

    if not shutil.which("node") or not (candidate.MODULES / "vite/bin/vite.js").is_file():
        pytest.skip("requires Node and installed desktop dependencies")
    monkeypatch.setenv("NODE_ENV", "development")
    output = tmp_path / "frontend"
    candidate.build_frontend(output)
    bundles = list((output / "assets").glob("*.js"))
    assert (output / "index.html").is_file() and bundles
    javascript = "\n".join(path.read_text(encoding="utf-8") for path in bundles)
    assert "Development result previews" not in javascript
    assert "Diagnose connection" in javascript
    assert os.environ["NODE_ENV"] == "development"


@pytest.mark.parametrize("output", ["missing", "wrong_architecture", "success"])
def test_fresh_output_is_required_before_replacing_existing_sidecar(packaging, tmp_path, monkeypatch, output):
    builder, _, _ = packaging
    monkeypatch.setattr(builder, "require_native_x64", lambda: None)
    monkeypatch.setattr(builder, "source_state", lambda: {"commit": "current", "dirty": False})
    monkeypatch.setattr(builder, "BUILD_DIR", tmp_path / "scratch")
    destination = tmp_path / builder.SIDECAR
    destination.write_bytes(b"old file")

    def simulate_pyinstaller(args, **kwargs):
        stage = Path(args[args.index("--distpath") + 1])
        assert not (stage / builder.SIDECAR).exists()
        if output == "wrong_architecture":
            (stage / builder.SIDECAR).write_bytes(executable(0x14C))
        elif output == "success":
            (stage / builder.SIDECAR).write_bytes(executable())

    monkeypatch.setattr(builder.subprocess, "run", simulate_pyinstaller)
    if output == "success":
        record = builder.build_sidecar(tmp_path)
        assert record["sha256"] == builder.file_digest(destination)
        assert record["commit"] == "current"
        assert record["target"] == builder.TARGET
        assert destination.read_bytes() == executable()
    else:
        with pytest.raises(RuntimeError, match="fresh file|not an x64"):
            builder.build_sidecar(tmp_path)
        assert destination.read_bytes() == b"old file"
    assert not list(builder.BUILD_DIR.iterdir())


def test_nsis_preflight_rejects_missing_cache_before_bundling(packaging, tmp_path):
    _, require_nsis, _ = packaging
    with pytest.raises(RuntimeError, match="NSIS cache incomplete.*makensis.exe"):
        require_nsis(tmp_path)


def test_nsis_script_must_reference_the_exact_verified_sidecar(packaging, tmp_path):
    builder, _, verify = packaging
    sidecar = tmp_path / builder.SIDECAR
    sidecar.write_bytes(executable())
    script = tmp_path / "installer.nsi"
    script.write_text(f'  File /a "/oname=whyfi-engine.exe" "{sidecar}"\n', encoding="utf-8-sig")
    verify(script, sidecar)
    wrong = tmp_path / "other.exe"
    wrong.write_bytes(executable())
    with pytest.raises(RuntimeError, match="does not package"):
        verify(script, wrong)

def test_candidate_uses_fresh_nsis_outputs_and_records_verified_hashes(packaging, tmp_path, monkeypatch):
    import json
    import build_candidate as candidate

    builder, _, _ = packaging
    commit = "b" * 40
    source = {"commit": commit, "dirty": False}
    desktop = tmp_path / "desktop"
    tauri = desktop / "src-tauri"
    tauri.mkdir(parents=True)
    (tauri / "Cargo.lock").write_text("cargo", encoding="utf-8")
    (desktop / "package-lock.json").write_text("npm", encoding="utf-8")
    staged = tauri / builder.SIDECAR
    staged.write_bytes(executable())
    staged_hash = builder.file_digest(staged)

    monkeypatch.setattr(candidate, "ROOT", tmp_path)
    monkeypatch.setattr(candidate, "DESKTOP", desktop)
    monkeypatch.setattr(candidate, "source_state", lambda: source)
    monkeypatch.setattr(candidate, "build_sidecar", lambda: {
        **source, "path": str(staged), "sha256": staged_hash,
    })
    monkeypatch.setattr(candidate.subprocess, "check_output", lambda *a, **kw: "NotSigned\n")

    def simulate_command(args, **kwargs):
        if "nsis" not in args:
            return
        override = Path(args[args.index("--config") + 1])
        bundle = json.loads(override.read_text(encoding="utf-8"))["bundle"]
        assert bundle["targets"] == ["nsis"]
        assert bundle["windows"]["webviewInstallMode"]["type"] == "downloadBootstrapper"
        assert bundle["windows"]["nsis"]["installMode"] == "currentUser"
        assert args[-3:] == ["--", "--locked", "--offline"]
        assert kwargs["env"]["CARGO_NET_OFFLINE"] == "true"
        release = Path(kwargs["env"]["CARGO_TARGET_DIR"]) / builder.TARGET / "release"
        assert not release.exists()
        installer_dir = release / "bundle" / "nsis"
        installer_dir.mkdir(parents=True)
        (installer_dir / "whyfi_0.1.0_x64-setup.exe").write_bytes(executable(0x14C))
        (release / "whyfi.exe").write_bytes(executable())
        (release / "whyfi-engine.exe").write_bytes(staged.read_bytes())
        script_dir = release / "nsis" / "x64"
        script_dir.mkdir(parents=True)
        (script_dir / "installer.nsi").write_text(
            f'  File /a "/oname=whyfi-engine.exe" "{staged}"\n', encoding="utf-8-sig",
        )

    monkeypatch.setattr(candidate.subprocess, "run", simulate_command)
    output = candidate.build_candidate("0.1.0", {"python": "fixture"})
    manifest = json.loads((output / "candidate.json").read_text(encoding="utf-8"))
    assert manifest["source"] == source
    assert manifest["frontend"] == {"mode": "production", "node_env": "production"}
    assert manifest["artifacts"]["installer"]["pe_machine"] == "x86"
    assert manifest["artifacts"]["sidecar"]["sha256"] == staged_hash
    assert manifest["artifacts"]["desktop"]["signing"] == "NotSigned"
    assert staged_hash in (output / "SHA256SUMS").read_text(encoding="utf-8")
