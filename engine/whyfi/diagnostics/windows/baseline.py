"""Baseline network investigation for WHYFI."""

from __future__ import annotations

from collections.abc import Callable

from whyfi.diagnostics.windows.dns import check_dns
from whyfi.diagnostics.common.internet import check_internet_reachability
from whyfi.diagnostics.windows.local_config import check_local_config
from whyfi.diagnostics.windows.ping import ping_host
from whyfi.diagnostics.windows.primary import get_primary_connection
from whyfi.diagnostics.windows.wifi import get_wifi_connection
from whyfi.models.diagnostic import BaselineDiagnosticResult, DiagnosticError


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
    errors: list[DiagnosticError] = []

    # Local configuration is checked independently because it may reveal
    # problems even when Windows has no usable default route.
    _report_progress(
        progress,
        "Checking network configuration...",
    )

    try:
        local_config = check_local_config()
    except Exception as exc:
        errors.append(DiagnosticError(
            "local_config", f"Local configuration check failed: {exc}"
        ))

    _report_progress(
        progress,
        "Finding your active connection...",
    )

    try:
        connection = get_primary_connection()
    except Exception as exc:
        errors.append(DiagnosticError(
            "route", f"Primary connection discovery failed: {exc}"
        ))

    if connection is not None:
        _report_progress(
            progress,
            "Checking your router...",
        )

        try:
            gateway = ping_host(connection.gateway)
        except Exception as exc:
            errors.append(DiagnosticError(
                "gateway", f"Gateway test failed: {exc}", connection.gateway
            ))
        else:
            if gateway.reachable is None:
                errors.append(DiagnosticError(
                    "gateway",
                    gateway.error or "Gateway measurement unavailable.",
                    gateway.target,
                ))

        _report_progress(progress, "Checking Wi-Fi signal...")

        try:
            wifi = get_wifi_connection(
                connection.adapter_name, optional=connection.adapter_type != "wifi"
            )
        except Exception as exc:
            errors.append(DiagnosticError("wifi", f"Wi-Fi discovery failed: {exc}"))
        else:
            if wifi is not None:
                if wifi.connected is True:
                    connection.adapter_type = "wifi"
                elif wifi.connected is None and wifi.error:
                    errors.append(DiagnosticError("wifi", wifi.error, connection.adapter_name))

    _report_progress(
        progress,
        "Testing internet access...",
    )

    try:
        internet = check_internet_reachability()
    except Exception as exc:
        errors.append(DiagnosticError(
            "internet", f"Internet reachability test failed: {exc}"
        ))
    else:
        if (
            connection is None
            and not any(error.check == "route" for error in errors)
            and internet.reachable is True
        ):
            errors.append(DiagnosticError(
                "route_consistency",
                "No active IPv4 default route was found, but a public IPv4 target replied.",
            ))
        for probe in internet.probes:
            if probe.reachable is None:
                errors.append(DiagnosticError(
                    "internet",
                    probe.error or "Public ICMP measurement unavailable.",
                    probe.target,
                ))

    _report_progress(
        progress,
        "Checking DNS...",
    )

    try:
        dns = check_dns(
            primary_interface_index=connection.interface_index if connection else None
        )
    except Exception as exc:
        errors.append(DiagnosticError("dns", f"DNS diagnostic failed: {exc}"))
    else:
        if dns.healthy is None and dns.error:
            errors.append(DiagnosticError("dns", dns.error))
        if dns.attribution_error:
            errors.append(DiagnosticError("dns", dns.attribution_error))
        if dns.system_query is not None and dns.system_query.success is None:
            errors.append(DiagnosticError("dns", dns.system_query.error or "System lookup unavailable."))
        for query in dns.configured_queries:
            if query.success is None:
                errors.append(DiagnosticError(
                    "dns", query.error or "DNS query unavailable.", query.resolver
                ))

    completed = (
        connection is not None
        and gateway is not None
        and internet is not None
        and dns is not None
        and dns.measurements_complete
        and local_config is not None
        and internet.reachable is not None
        and not any(error.check in {"gateway", "internet"} for error in errors)
    )

    return BaselineDiagnosticResult(
        connection=connection,
        gateway=gateway,
        internet=internet,
        dns=dns,
        wifi=wifi,
        local_config=local_config,
        completed=completed,
        error="; ".join(error.message for error in errors) or None,
        collection_errors=errors,
    )
