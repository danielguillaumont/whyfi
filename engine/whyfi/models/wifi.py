"""Structured models for WHYFI Wi-Fi diagnostics."""

from dataclasses import dataclass


@dataclass(slots=True)
class WiFiConnection:
    """Represents the current Windows Wi-Fi connection."""

    connected: bool
    interface_name: str | None = None
    ssid: str | None = None
    signal_percent: int | None = None
    radio_type: str | None = None
    channel: int | None = None
    receive_rate_mbps: float | None = None
    transmit_rate_mbps: float | None = None
    error: str | None = None
