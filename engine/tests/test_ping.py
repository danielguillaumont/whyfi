"""Ping parsing and connection-quality tests for WHYFI."""

import subprocess

import pytest

from whyfi.diagnostics.windows import ping
from whyfi.diagnostics.windows.ping import _calculate_jitter


def test_calculate_jitter_from_stable_latencies() -> None:
    """Small latency changes should produce low jitter."""

    latencies = [10.0, 12.0, 11.0, 13.0]

    jitter = _calculate_jitter(latencies)

    assert jitter == 1.67


def test_calculate_jitter_from_unstable_latencies() -> None:
    """Large latency swings should produce high jitter."""

    latencies = [10.0, 50.0, 12.0, 45.0]

    jitter = _calculate_jitter(latencies)

    assert jitter == 37.0


def test_single_reply_has_no_jitter_measurement() -> None:
    """Jitter requires at least two successful replies."""

    assert _calculate_jitter([10.0]) is None


def test_empty_latency_list_has_no_jitter_measurement() -> None:
    """No replies should not produce a jitter value."""

    assert _calculate_jitter([]) is None


def test_windows_ping_collects_unlocalized_status_and_latency(monkeypatch) -> None:
    output = '[{"status":0,"elapsed":0},{"status":11010},{"status":0,"elapsed":12}]'

    def run(command, **kwargs):
        assert command[0] == "powershell.exe"
        assert "System.Net.NetworkInformation.Ping" in command[-1]
        return subprocess.CompletedProcess(command, 0, output, "")

    monkeypatch.setattr(ping.subprocess, "run", run)
    result = ping.ping_host("192.0.2.1", count=3)

    assert result.reachable is True
    assert result.packets_received == 2
    assert result.packet_loss_percent == 33.3
    assert result.min_latency_ms == 0.5
    assert result.average_latency_ms == 6.25
    assert result.jitter_ms == 11.5


def test_windows_ping_reports_genuine_no_reply(monkeypatch) -> None:
    output = '[{"status":11010},{"status":11003}]'
    monkeypatch.setattr(
        ping.subprocess, "run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 0, output, ""),
    )

    result = ping.ping_host("192.0.2.1", count=2)

    assert result.reachable is False
    assert result.packets_sent == 2
    assert result.packets_received == 0
    assert result.packet_loss_percent == 100.0


@pytest.mark.parametrize(("exit_code", "stdout", "stderr", "reason"), [
    (1, "", "permission denied", "permission denied"),
    (0, '[{"status":11010}]', "unexpected error", "unexpected error"),
    (0, "Antwort: Zeit=12ms", "", "Invalid Windows ICMP output"),
    (0, "[]", "", "Expected 1 ICMP samples"),
    (0, '[{"status":11050}]', "", "Windows status 11050"),
    (0, '[{"status":0,"elapsed":-1}]', "", "Invalid ICMP round-trip time"),
])
def test_windows_ping_failure_has_no_reachability_or_loss(
    monkeypatch, exit_code, stdout, stderr, reason
) -> None:
    monkeypatch.setattr(
        ping.subprocess, "run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, exit_code, stdout, stderr),
    )

    result = ping.ping_host("192.0.2.1", count=1)

    assert result.reachable is None
    assert result.packets_sent is None
    assert result.packets_received is None
    assert result.packet_loss_percent is None
    assert reason in result.error


@pytest.mark.parametrize(("error", "reason"), [
    (subprocess.TimeoutExpired("powershell.exe", 10), "timed out"),
    (FileNotFoundError("missing executable"), "missing executable"),
])
def test_windows_ping_process_error_is_unavailable(monkeypatch, error, reason) -> None:
    def run(*args, **kwargs):
        raise error

    monkeypatch.setattr(ping.subprocess, "run", run)
    result = ping.ping_host("192.0.2.1", count=1)

    assert result.reachable is None
    assert result.packet_loss_percent is None
    assert reason in result.error
