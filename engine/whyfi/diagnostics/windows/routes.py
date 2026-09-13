"""Windows default-route discovery for WHYFI."""

from __future__ import annotations

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
$routes = Get-NetRoute `
    -AddressFamily IPv4 `
    -DestinationPrefix '0.0.0.0/0' `
    -ErrorAction SilentlyContinue

$results = foreach ($route in $routes) {
    $interface = Get-NetIPInterface `
        -InterfaceIndex $route.InterfaceIndex `
        -AddressFamily IPv4 `
        -ErrorAction SilentlyContinue

    if ($null -ne $interface -and $interface.ConnectionState -eq 'Connected') {
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

$results |
    Sort-Object TotalMetric |
    Select-Object -First 1 |
    ConvertTo-Json -Compress
"""

    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            command,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        check=False,
    )

    if completed.returncode != 0:
        return None

    output = completed.stdout.strip()

    if not output:
        return None

    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return None

    return DefaultRoute(
        interface_alias=str(data["InterfaceAlias"]),
        interface_index=int(data["InterfaceIndex"]),
        gateway=str(data["Gateway"]),
        route_metric=int(data["RouteMetric"]),
        interface_metric=int(data["InterfaceMetric"]),
        total_metric=int(data["TotalMetric"]),
    )
