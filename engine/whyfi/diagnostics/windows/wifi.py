"""Windows Wi-Fi connection discovery for WHYFI."""

from __future__ import annotations

import subprocess

from whyfi.models.wifi import WiFiConnection


def _parse_signal(value: str | None) -> int | None:
    """Convert a Windows Wi-Fi signal value such as '87%' to an integer."""

    if value is None:
        return None

    try:
        return int(value.strip().rstrip("%"))
    except ValueError:
        return None


def _parse_float(value: str | None) -> float | None:
    """Convert a numeric netsh value to a float."""

    if value is None:
        return None

    try:
        return float(value.strip())
    except ValueError:
        return None


def _parse_int(value: str | None) -> int | None:
    """Convert a numeric netsh value to an integer."""

    if value is None:
        return None

    try:
        return int(value.strip())
    except ValueError:
        return None


def get_wifi_connection() -> WiFiConnection:
    """Return details about the current Windows Wi-Fi connection."""

    try:
        completed = subprocess.run(
            [
                "netsh.exe",
                "wlan",
                "show",
                "interfaces",
            ],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=10,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return WiFiConnection(
            connected=False,
            error="Wi-Fi discovery timed out.",
        )
    except OSError as exc:
        return WiFiConnection(
            connected=False,
            error=str(exc),
        )

    if completed.returncode != 0:
        error = completed.stderr.strip() or completed.stdout.strip()

        return WiFiConnection(
            connected=False,
            error=error or "Windows Wi-Fi discovery failed.",
        )

    output = completed.stdout.strip()

    if not output:
        return WiFiConnection(
            connected=False,
            error="Windows returned no Wi-Fi information.",
        )

    fields: dict[str, str] = {}

    wanted_fields = {
        "name",
        "state",
        "ssid",
        "radio type",
        "channel",
        "receive rate (mbps)",
        "transmit rate (mbps)",
        "signal",
    }

    for line in output.splitlines():
        if ":" not in line:
            continue

        key, value = line.split(":", 1)

        normalized_key = key.strip().lower()

        if normalized_key in wanted_fields and normalized_key not in fields:
            fields[normalized_key] = value.strip()

    interface_name = fields.get("name")
    state = fields.get("state", "").lower()

    if state != "connected":
        return WiFiConnection(
            connected=False,
            interface_name=interface_name,
            error="Wi-Fi interface is not currently connected.",
        )

    return WiFiConnection(
        connected=True,
        interface_name=interface_name,
        ssid=fields.get("ssid"),
        signal_percent=_parse_signal(fields.get("signal")),
        radio_type=fields.get("radio type"),
        channel=_parse_int(fields.get("channel")),
        receive_rate_mbps=_parse_float(
            fields.get("receive rate (mbps)")
        ),
        transmit_rate_mbps=_parse_float(
            fields.get("transmit rate (mbps)")
        ),
    )
