"""Tests for missing evidence across Windows probes, diagnosis, and CLI output."""

import json
import subprocess
import sys
from types import SimpleNamespace

import pytest

from whyfi import __main__ as cli
from whyfi.diagnosis.engine import diagnose_baseline
from whyfi.diagnosis.quality import diagnose_connection_quality
from whyfi.diagnostics.common import internet
from whyfi.diagnostics.windows import baseline, primary, quality, routes
from whyfi.models.diagnosis import DiagnosisCode
from whyfi.models.dns import DNSDiagnosticResult
from whyfi.models.local_config import LocalConfigResult
from whyfi.models.probes import PingResult


@pytest.fixture
def baseline_probes(monkeypatch):
    monkeypatch.setattr(baseline, "check_local_config", lambda: LocalConfigResult(True))
    monkeypatch.setattr(baseline, "get_wifi_connection", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        baseline, "check_dns", lambda **kwargs: DNSDiagnosticResult(True, None, None)
    )
    monkeypatch.setattr(
        internet, "ping_host", lambda target: PingResult(target, True, 4, 4, 0.0)
    )


@pytest.mark.parametrize(("exit_code", "stdout", "stderr", "reason"), [
    (1, "[]", "access denied", "access denied"),
    (0, "[]", "Windows route error", "Windows route error"),
    (0, "", "", "Invalid Windows route output"),
    (0, "not JSON", "", "Invalid Windows route output"),
    (0, "null", "", "Expected zero or one preferred route"),
    (0, "[{}]", "", "InterfaceAlias"),
])
def test_failed_route_collection_reaches_the_desktop_result_contract(
    monkeypatch, capsys, baseline_probes, exit_code, stdout, stderr, reason
) -> None:
    monkeypatch.setattr(
        routes.subprocess, "run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, exit_code, stdout, stderr),
    )
    monkeypatch.setattr(sys, "argv", ["whyfi", "--stream-json"])

    cli.main()

    events = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    result = events[-1]
    assert result["type"] == "result"
    assert result["diagnosis"]["code"] == "unknown"
    assert result["diagnosis"]["confidence"] is None
    assert reason in result["diagnosis"]["evidence"][0]
    assert result["details"]["completed"] is False
    error, = result["details"]["collection_errors"]
    assert error["check"] == "route"
    assert reason in error["message"]


def test_route_timeout_is_inconclusive_in_plain_cli(monkeypatch, capsys, baseline_probes) -> None:
    def run(*args, **kwargs):
        raise subprocess.TimeoutExpired("powershell.exe", 10)

    monkeypatch.setattr(routes.subprocess, "run", run)
    monkeypatch.setattr(sys, "argv", ["whyfi"])

    cli.main()

    output = capsys.readouterr().out
    assert "The diagnosis is inconclusive." in output
    assert "timed out" in output
    assert "Confidence:" not in output


def test_missing_route_and_no_public_replies_support_disconnection(
    monkeypatch, baseline_probes
) -> None:
    monkeypatch.setattr(
        routes.subprocess, "run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 0, "[]", ""),
    )
    monkeypatch.setattr(
        internet, "ping_host", lambda target: PingResult(target, False, 4, 0, 100.0)
    )

    result = baseline.run_baseline_diagnostics()
    diagnosis = diagnose_baseline(result)

    assert result.collection_errors == []
    assert diagnosis.code is DiagnosisCode.NO_CONNECTION
    assert diagnosis.confidence == 98


def test_missing_route_with_public_replies_is_inconclusive(
    monkeypatch, capsys, baseline_probes
) -> None:
    monkeypatch.setattr(
        routes.subprocess, "run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 0, "[]", ""),
    )
    monkeypatch.setattr(sys, "argv", ["whyfi", "--json"])

    cli.main()

    result = json.loads(capsys.readouterr().out)
    assert result["diagnosis"]["code"] == "unknown"
    assert result["diagnosis"]["confidence"] is None
    assert result["diagnosis"]["evidence"] == [
        "No active IPv4 default route was found.",
        "Public IPv4 targets reachable: 2.",
    ]
    assert result["details"]["connection"] is None
    assert result["details"]["internet"]["reachable"] is True
    error, = result["details"]["collection_errors"]
    assert error["check"] == "route_consistency"
    assert "public IPv4 target replied" in error["message"]


def test_missing_route_without_public_measurements_is_inconclusive(
    monkeypatch, baseline_probes
) -> None:
    monkeypatch.setattr(
        routes.subprocess, "run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 0, "[]", ""),
    )
    monkeypatch.setattr(
        internet, "ping_host",
        lambda target: PingResult(target, None, None, None, None, error="ICMP unavailable"),
    )

    diagnosis = diagnose_baseline(baseline.run_baseline_diagnostics())

    assert diagnosis.code is DiagnosisCode.UNKNOWN
    assert diagnosis.confidence is None
    assert "No active IPv4 default route was found." in diagnosis.evidence


def test_active_route_preserves_unicode_interface_alias(monkeypatch) -> None:
    output = json.dumps([{
        "InterfaceAlias": "Réseau",
        "InterfaceIndex": 7,
        "Gateway": "192.0.2.1",
        "RouteMetric": 0,
        "InterfaceMetric": 25,
        "TotalMetric": 25,
    }], ensure_ascii=False)
    monkeypatch.setattr(
        routes.subprocess, "run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 0, output, ""),
    )

    route = routes.get_default_route()

    assert route is not None
    assert route.interface_alias == "Réseau"
    assert route.gateway == "192.0.2.1"


def test_route_adapter_mismatch_is_inconclusive(monkeypatch, baseline_probes) -> None:
    monkeypatch.setattr(
        primary, "get_default_route",
        lambda: routes.DefaultRoute("LAN", 7, "192.0.2.1", 0, 25, 25),
    )
    monkeypatch.setattr(primary, "get_network_adapters", list)

    result = baseline.run_baseline_diagnostics()

    assert diagnose_baseline(result).code is DiagnosisCode.UNKNOWN
    error, = result.collection_errors
    assert error.check == "route"
    assert "LAN" in error.message


@pytest.mark.parametrize(("failed_check", "code"), [
    (None, DiagnosisCode.HEALTHY),
    ("gateway", DiagnosisCode.UNKNOWN),
    ("internet", DiagnosisCode.UNKNOWN),
])
def test_baseline_does_not_treat_unavailable_icmp_as_loss(
    monkeypatch, baseline_probes, failed_check, code
) -> None:
    gateway = "192.0.2.1"
    monkeypatch.setattr(
        baseline, "get_primary_connection",
        lambda: SimpleNamespace(
            gateway=gateway, adapter_type="ethernet", adapter_name="LAN", interface_index=7
        ),
    )

    def ping(target):
        if (failed_check == "gateway" and target == gateway) or (
            failed_check == "internet" and target == "1.1.1.1"
        ):
            return PingResult(target, None, None, None, None, error="Invalid ICMP output")
        return PingResult(target, True, 4, 4, 0.0)

    monkeypatch.setattr(baseline, "ping_host", ping)
    monkeypatch.setattr(internet, "ping_host", ping)

    result = baseline.run_baseline_diagnostics()
    diagnosis = diagnose_baseline(result)

    assert diagnosis.code is code
    if failed_check is None:
        assert result.completed is True
        assert diagnosis.confidence == 96
    else:
        assert result.completed is False
        assert diagnosis.confidence is None
        error, = result.collection_errors
        assert error.check == failed_check
        assert error.target == (gateway if failed_check == "gateway" else "1.1.1.1")


def test_unavailable_public_probe_does_not_confirm_internet_outage(monkeypatch) -> None:
    samples = {
        "1.1.1.1": PingResult("1.1.1.1", None, None, None, None, error="Command failed"),
        "8.8.8.8": PingResult("8.8.8.8", False, 4, 0, 100.0),
    }
    monkeypatch.setattr(internet, "ping_host", samples.__getitem__)

    result = internet.check_internet_reachability()

    assert result.reachable is None
    assert result.targets_tested == 1
    assert result.targets_reachable == 0


def test_quality_mode_preserves_probe_failure(monkeypatch) -> None:
    monkeypatch.setattr(
        quality, "get_primary_connection", lambda: SimpleNamespace(gateway="192.0.2.1")
    )
    monkeypatch.setattr(
        quality, "ping_host",
        lambda target, count: PingResult(target, None, None, None, None, error="ICMP unavailable"),
    )

    result = quality.check_connection_quality()
    diagnosis = diagnose_connection_quality(result)

    assert result.healthy is False
    assert diagnosis.code is DiagnosisCode.UNKNOWN
    assert diagnosis.confidence is None
    assert "192.0.2.1: ICMP unavailable" in diagnosis.evidence[0]


@pytest.mark.parametrize(("jitter", "unavailable_targets", "expected"), [
    (30.0, {"1.1.1.1"}, DiagnosisCode.UNSTABLE_CONNECTION),
    (30.0, {"1.1.1.1", "8.8.8.8"}, DiagnosisCode.UNSTABLE_CONNECTION),
    (2.0, {"1.1.1.1", "8.8.8.8"}, DiagnosisCode.UNKNOWN),
    (2.0, {"1.1.1.1"}, DiagnosisCode.UNKNOWN),
    (2.0, set(), DiagnosisCode.HEALTHY),
])
def test_quality_preserves_gateway_evidence_independently(
    monkeypatch, jitter, unavailable_targets, expected
) -> None:
    gateway = "192.0.2.1"
    monkeypatch.setattr(
        quality, "get_primary_connection", lambda: SimpleNamespace(gateway=gateway)
    )

    def ping(target, count):
        if target in unavailable_targets:
            return PingResult(target, None, None, None, None, error="command failed")
        return PingResult(
            target, True, count, count, 0.0, jitter_ms=jitter if target == gateway else 2.0
        )

    monkeypatch.setattr(quality, "ping_host", ping)

    result = quality.check_connection_quality()
    diagnosis = diagnose_connection_quality(result)

    assert result.gateway_unstable is (jitter >= 15.0)
    assert result.healthy is (expected is DiagnosisCode.HEALTHY)
    assert result.internet_unstable is False
    assert diagnosis.code is expected
    assert (diagnosis.confidence is None) is (expected is DiagnosisCode.UNKNOWN)
    for probe in result.internet_probes:
        if probe.target in unavailable_targets:
            assert probe.reachable is None
            assert probe.average_latency_ms is None
            assert probe.packet_loss_percent is None
            assert f"{probe.target}: command failed" in diagnosis.evidence
