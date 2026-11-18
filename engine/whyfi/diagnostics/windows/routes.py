"""Windows default-route discovery for WHYFI."""

from __future__ import annotations

import ipaddress
import json
import subprocess
from dataclasses import dataclass


@dataclass(slots=True)
class DefaultRoute:
    """Represents the active IPv4 default route used by Windows."""

    interface_alias: str
    interface_index: int
    gateway: str
    route_metric: int
    interface_metric: int
    total_metric: int


def get_default_route() -> DefaultRoute | None:
    """Return the preferred active IPv4 default route."""

    command = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$routes = Get-NetRoute -AddressFamily IPv4 |
    Where-Object DestinationPrefix -eq '0.0.0.0/0'

$results = foreach ($route in $routes) {
    $interface = Get-NetIPInterface `
        -InterfaceIndex $route.InterfaceIndex `
        -AddressFamily IPv4

    if ($null -eq $interface) {
        throw "Could not read IPv4 interface $($route.InterfaceIndex)."
    }

    if ($interface.ConnectionState -eq 'Connected') {
        [PSCustomObject]@{
            InterfaceAlias  = $route.InterfaceAlias
            InterfaceIndex  = $route.InterfaceIndex
            Gateway         = $route.NextHop
            RouteMetric     = $route.RouteMetric
            InterfaceMetric = $interface.InterfaceMetric
            TotalMetric     = $route.RouteMetric + $interface.InterfaceMetric
        }
    }
}

$preferred = @($results |
    Sort-Object TotalMetric |
    Select-Object -First 1)
ConvertTo-Json -InputObject $preferred -Compress
"""

    try:
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Windows route command timed out.") from exc
    except OSError as exc:
        raise RuntimeError(f"Could not run Windows route command: {exc}") from exc

    if completed.returncode != 0 or completed.stderr.strip():
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(
            f"Windows route command failed (exit {completed.returncode}): {detail}"
        )

    try:
        routes = json.loads(completed.stdout)
        if routes == []:
            return None
        if not isinstance(routes, list) or len(routes) != 1:
            raise ValueError("Expected zero or one preferred route.")
        data = routes[0]
        alias = data["InterfaceAlias"]
        if not isinstance(alias, str) or not alias.strip():
            raise ValueError("Missing interface alias.")

        index = data["InterfaceIndex"]
        route_metric = data["RouteMetric"]
        interface_metric = data["InterfaceMetric"]
        total_metric = data["TotalMetric"]
        if any(
            type(value) is not int or value < 0
            for value in (index, route_metric, interface_metric, total_metric)
        ) or index == 0:
            raise ValueError("Invalid interface index or route metrics.")
        gateway = data["Gateway"]
        if not isinstance(gateway, str):
            raise ValueError("Invalid IPv4 next hop.")

        return DefaultRoute(
            interface_alias=alias,
            interface_index=index,
            gateway=str(ipaddress.IPv4Address(gateway)),
            route_metric=route_metric,
            interface_metric=interface_metric,
            total_metric=total_metric,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"Invalid Windows route output: {exc}") from exc
