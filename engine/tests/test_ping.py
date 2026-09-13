"""Ping parsing and connection-quality tests for WHYFI."""

from whyfi.diagnostics.windows.ping import (
    _calculate_jitter,
    _extract_latencies,
)


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


def test_extract_windows_ping_latencies() -> None:
    """Windows ping reply lines should produce latency measurements."""

    output = """
Reply from 1.1.1.1: bytes=32 time=18ms TTL=57
Reply from 1.1.1.1: bytes=32 time=20ms TTL=57
Reply from 1.1.1.1: bytes=32 time=17ms TTL=57
"""

    assert _extract_latencies(output) == [18.0, 20.0, 17.0]


def test_extract_less_than_one_millisecond_latency() -> None:
    """Windows time<1ms replies should use WHYFI's 0.5 ms estimate."""

    output = "Reply from 192.168.1.1: bytes=32 time<1ms TTL=64"

    assert _extract_latencies(output) == [0.5]
