"""Wi-Fi signal assessment rules for WHYFI."""

from __future__ import annotations


_WEAK_SIGNAL_THRESHOLD_PERCENT = 40


def is_weak_wifi_signal(signal_percent: int | None) -> bool:
    """Return True when Windows reports a weak Wi-Fi signal."""

    if signal_percent is None:
        return False

    return signal_percent <= _WEAK_SIGNAL_THRESHOLD_PERCENT


def describe_wifi_signal(signal_percent: int | None) -> str:
    """Return a simple human-readable Wi-Fi signal description."""

    if signal_percent is None:
        return "unknown"

    if signal_percent <= 40:
        return "weak"

    if signal_percent <= 65:
        return "fair"

    if signal_percent <= 85:
        return "good"

    return "excellent"
