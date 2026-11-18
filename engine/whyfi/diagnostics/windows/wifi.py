"""Windows Wi-Fi connection discovery for WHYFI."""

from __future__ import annotations

import math
import re
import subprocess

from whyfi.models.wifi import WiFiConnection


_INTERFACE_COUNT = re.compile(
    r"there (?:is|are) (\d+) interfaces? on the system:", re.IGNORECASE
)
_FIELDS = {
    "state", "ssid", "radio type", "channel", "receive rate (mbps)",
    "transmit rate (mbps)", "signal",
}


def _parse_signal(value: str | None) -> int | None:
    """Convert a Windows Wi-Fi signal value such as '87%' to an integer."""

    if value is None:
        return None

    try:
        percent = int(value.strip().rstrip("%"))
        return percent if 0 <= percent <= 100 else None
    except ValueError:
        return None


def _parse_float(value: str | None) -> float | None:
    """Convert a numeric netsh value to a float."""

    if value is None:
        return None

    try:
        rate = float(value.strip())
        return rate if math.isfinite(rate) and rate >= 0 else None
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


def _parse_interfaces(output: str) -> list[dict[str, str]]:
    if output.casefold() == "there is no wireless interface on the system.":
        return []

    records: list[dict[str, str]] = []
    expected_count = None
    for line in output.splitlines():
        line = line.strip()
        count = _INTERFACE_COUNT.fullmatch(line)
        if count:
            if expected_count is not None or records:
                raise ValueError("Unexpected Wi-Fi interface count in netsh output.")
            expected_count = int(count[1])
            continue
        if line.startswith("Hosted network status"):
            break
        key, separator, value = line.partition(":")
        if not separator:
            continue
        key = key.strip().casefold()
        if key == "name":
            records.append({"name": value.strip()})
        elif key in _FIELDS:
            if not records or key in records[-1]:
                raise ValueError("Malformed Wi-Fi interface record.")
            records[-1][key] = value.strip()

    if expected_count is None:
        raise ValueError("Missing Wi-Fi interface count in netsh output.")
    if expected_count != len(records):
        raise ValueError("Wi-Fi interface count did not match the output.")
    if not records and not _INTERFACE_COUNT.fullmatch(output):
        raise ValueError("Unrecognized netsh output for zero Wi-Fi interfaces.")
    if any(
        not record["name"]
        or record.get("state", "").casefold() not in {"connected", "disconnected"}
        for record in records
    ):
        raise ValueError("Missing or unrecognized Wi-Fi interface name or state.")
    return records


def get_wifi_connection(
    primary_adapter_name: str | None = None, *, optional: bool = False
) -> WiFiConnection | None:
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
            connected=None,
            error="Wi-Fi discovery timed out.",
        )
    except OSError as exc:
        return WiFiConnection(
            connected=None,
            error=f"Could not run Wi-Fi discovery: {exc}",
        )

    if completed.returncode != 0 or completed.stderr.strip():
        error = completed.stderr.strip() or completed.stdout.strip()

        return WiFiConnection(
            connected=None,
            error=f"Windows Wi-Fi discovery failed (exit {completed.returncode}): {error}",
        )

    try:
        records = _parse_interfaces(completed.stdout.strip())
    except ValueError as exc:
        return WiFiConnection(connected=None, error=str(exc))

    if optional and primary_adapter_name is not None and not any(
        record["name"].casefold() == primary_adapter_name.casefold()
        for record in records
    ):
        return None

    connected = [record for record in records if record["state"].casefold() == "connected"]
    if not connected:
        return WiFiConnection(connected=False)

    candidates = connected
    if primary_adapter_name is not None:
        candidates = [
            record for record in connected
            if record["name"].casefold() == primary_adapter_name.casefold()
        ]
    if len(candidates) != 1:
        names = ", ".join(sorted(record["name"] for record in connected))
        return WiFiConnection(
            connected=None,
            error=(
                f"Could not select a Wi-Fi interface without a primary adapter: {names}."
                if primary_adapter_name is None else
                f"Could not uniquely match primary adapter {primary_adapter_name} "
                f"to a connected Wi-Fi interface. Connected interfaces: {names}."
            ),
        )

    fields = candidates[0]
    return WiFiConnection(
        connected=True,
        interface_name=fields["name"],
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
