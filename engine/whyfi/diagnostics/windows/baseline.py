"""Baseline network investigation for WHYFI."""

from __future__ import annotations

from whyfi.diagnostics.common.dns import check_dns
from whyfi.diagnostics.common.internet import check_internet_reachability
from whyfi.diagnostics.windows.ping import ping_host
from whyfi.diagnostics.windows.primary import get_primary_connection
from whyfi.diagnostics.windows.wifi import get_wifi_connection
from whyfi.models.diagnostic import BaselineDiagnosticResult


def run_baseline_diagnostics() -> BaselineDiagnosticResult:
    """Run WHYFI's initial network health investigation."""

    connection = None
    gateway = None
    internet = None
    dns = None
    wifi = None
    errors: list[str] = []

    try:
        connection = get_primary_connection()
    except Exception as exc:
        errors.append(f"Primary connection discovery failed: {exc}")

    if connection is not None:
        try:
            gateway = ping_host(connection.gateway)
        except Exception as exc:
            errors.append(f"Gateway test failed: {exc}")

        if connection.adapter_type == "wifi":
            try:
                wifi = get_wifi_connection()
            except Exception as exc:
                errors.append(f"Wi-Fi discovery failed: {exc}")
    else:
        errors.append("No primary network connection was found.")

    try:
        internet = check_internet_reachability()
    except Exception as exc:
        errors.append(f"Internet reachability test failed: {exc}")

    try:
        dns = check_dns()
    except Exception as exc:
        errors.append(f"DNS diagnostic failed: {exc}")

    completed = (
        connection is not None
        and gateway is not None
        and internet is not None
        and dns is not None
    )

    return BaselineDiagnosticResult(
        connection=connection,
        gateway=gateway,
        internet=internet,
        dns=dns,
        wifi=wifi,
        completed=completed,
        error="; ".join(errors) if errors else None,
    )
