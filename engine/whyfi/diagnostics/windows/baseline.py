"""Baseline network investigation for WHYFI."""

from __future__ import annotations

from collections.abc import Callable

from whyfi.diagnostics.common.dns import check_dns
from whyfi.diagnostics.common.internet import check_internet_reachability
from whyfi.diagnostics.windows.local_config import check_local_config
from whyfi.diagnostics.windows.ping import ping_host
from whyfi.diagnostics.windows.primary import get_primary_connection
from whyfi.diagnostics.windows.wifi import get_wifi_connection
from whyfi.models.diagnostic import BaselineDiagnosticResult


ProgressCallback = Callable[[str], None]


def _report_progress(
    progress: ProgressCallback | None,
    message: str,
) -> None:
    """Send a progress message when a callback is available."""

    if progress is not None:
        progress(message)


def run_baseline_diagnostics(
    progress: ProgressCallback | None = None,
) -> BaselineDiagnosticResult:
    """Run WHYFI's initial network health investigation."""

    connection = None
    gateway = None
    internet = None
    dns = None
    wifi = None
    local_config = None
    errors: list[str] = []

    # Local configuration is checked independently because it may reveal
    # problems even when Windows has no usable default route.
    _report_progress(
        progress,
        "Checking network configuration...",
    )

    try:
        local_config = check_local_config()
    except Exception as exc:
        errors.append(f"Local configuration check failed: {exc}")

    _report_progress(
        progress,
        "Finding your active connection...",
    )

    try:
        connection = get_primary_connection()
    except Exception as exc:
        errors.append(f"Primary connection discovery failed: {exc}")

    if connection is not None:
        _report_progress(
            progress,
            "Checking your router...",
        )

        try:
            gateway = ping_host(connection.gateway)
        except Exception as exc:
            errors.append(f"Gateway test failed: {exc}")

        if connection.adapter_type == "wifi":
            _report_progress(
                progress,
                "Checking Wi-Fi signal...",
            )

            try:
                wifi = get_wifi_connection()
            except Exception as exc:
                errors.append(f"Wi-Fi discovery failed: {exc}")
    else:
        errors.append("No primary network connection was found.")

    _report_progress(
        progress,
        "Testing internet access...",
    )

    try:
        internet = check_internet_reachability()
    except Exception as exc:
        errors.append(f"Internet reachability test failed: {exc}")

    _report_progress(
        progress,
        "Checking DNS...",
    )

    try:
        dns = check_dns()
    except Exception as exc:
        errors.append(f"DNS diagnostic failed: {exc}")

    completed = (
        connection is not None
        and gateway is not None
        and internet is not None
        and dns is not None
        and local_config is not None
    )

    return BaselineDiagnosticResult(
        connection=connection,
        gateway=gateway,
        internet=internet,
        dns=dns,
        wifi=wifi,
        local_config=local_config,
        completed=completed,
        error="; ".join(errors) if errors else None,
    )
