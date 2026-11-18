"""Windows DNS-client evidence and interface-scoped direct measurements."""

from __future__ import annotations

import ipaddress
import subprocess

from whyfi.diagnostics.common import dns
from whyfi.models.dns import (
    DNSDiagnosticResult,
    SystemDNSQueryResult,
    WindowsDNSResolverEvidence,
)

_HOSTNAME = "example.com."


def query_windows_dns_client() -> SystemDNSQueryResult:
    """Ask the Windows DNS client without naming an upstream resolver."""
    script = """
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
try {
    $addresses = @(Resolve-DnsName -Name 'example.com.' -Type A -DnsOnly -NoHostsFile |
        Where-Object Type -eq 'A' | ForEach-Object { $_.IPAddress })
    $result = @{ addresses = $addresses; code = $null }
} catch {
    $result = @{ addresses = @(); code = ($_.FullyQualifiedErrorId -split ',')[0] }
}
ConvertTo-Json -InputObject $result -Compress
"""
    try:
        result = dns._windows_json(script, timeout=8)
        if (
            not isinstance(result, dict) or "code" not in result
            or not isinstance(result.get("addresses"), list)
        ):
            raise ValueError("Unrecognized Windows DNS-client output.")
        addresses = result["addresses"]
        if any(not isinstance(address, str) or ipaddress.ip_address(address).version != 4
               for address in addresses):
            raise ValueError("Invalid address in Windows DNS-client output.")
        code = result.get("code")
        if addresses and code is None:
            return SystemDNSQueryResult(_HOSTNAME, True, addresses)
        if code is None and not addresses:
            return SystemDNSQueryResult(_HOSTNAME, False, error="No IPv4 answer returned.")
        if not isinstance(code, str) or not code or addresses:
            raise ValueError("Invalid Windows DNS-client status.")
        failed = code in {
            "DNS_ERROR_RCODE_NAME_ERROR", "DNS_ERROR_RCODE_SERVER_FAILURE",
            "DNS_ERROR_RCODE_REFUSED", "DNS_INFO_NO_RECORDS",
        }
        return SystemDNSQueryResult(
            _HOSTNAME, False if failed else None, error=f"Windows DNS client: {code[:160]}"
        )
    except subprocess.TimeoutExpired:
        error = "Windows DNS-client lookup exceeded its eight-second collection deadline."
    except (OSError, RuntimeError, ValueError) as exc:
        error = f"Windows DNS-client lookup unavailable: {exc}"
    return SystemDNSQueryResult(_HOSTNAME, None, error=error)


def _route_prefixes(routes: object) -> list[tuple[int, ipaddress.IPv4Network | ipaddress.IPv6Network]] | None:
    if not isinstance(routes, list) or not routes:
        return None
    if any(
        not isinstance(route, dict) or type(route.get("index")) is not int
        or not isinstance(route.get("prefix"), str)
        for route in routes
    ):
        return None
    try:
        return [
            (route["index"], ipaddress.ip_network(route["prefix"]))
            for route in routes
        ]
    except ValueError:
        return None


def check_dns(*, primary_interface_index: int | None) -> DNSDiagnosticResult:
    system_query = query_windows_dns_client()
    try:
        inventory = dns.get_windows_dns_inventory()
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
        return DNSDiagnosticResult(
            None, None, None, system_query=system_query,
            attribution_error=f"Windows DNS interface inventory unavailable: {exc}",
        )

    rows = inventory["interfaces"]
    routes = _route_prefixes(inventory.get("routes"))
    policy = inventory.get("policy")
    evidence = []
    direct = []
    unavailable = {}
    errors = []
    primary_rows = [row for row in rows if row["index"] == primary_interface_index]
    primary_verified = (
        any(row["family"] == 2 for row in primary_rows)
        and len({row["alias"].casefold() for row in primary_rows}) == 1
        and len({row["family"] for row in primary_rows}) == len(primary_rows)
    )
    if not primary_verified:
        errors.append("The primary Windows IPv4 interface could not be verified.")
    if any(row["servers"] is None for row in rows):
        errors.append("Windows returned incomplete DNS interface records.")
    if policy is not False:
        errors.append("Windows DNS namespace policy is active or could not be verified.")
    if routes is None:
        errors.append("Windows DNS routing context could not be verified.")

    for row in sorted(rows, key=lambda item: (item["index"], item["family"])):
        primary = primary_verified and row["index"] == primary_interface_index
        for server in row["servers"] or ():
            server = dns.scoped_resolver(server, row["index"])
            scope = None
            on_interface = None
            ambiguous_route = False
            if routes is not None:
                try:
                    address = ipaddress.ip_address(server)
                    scope = getattr(address, "scope_id", None)
                    expected_version = 4 if row["family"] == 2 else 6
                    if address.version != expected_version:
                        raise ValueError("resolver address family mismatch")
                    matches = [
                        (index, prefix.prefixlen) for index, prefix in routes
                        if address.version == prefix.version and address in prefix
                        and (not address.is_link_local or scope is None or scope == str(index))
                    ]
                    own = max((size for index, size in matches if index == row["index"]), default=-1)
                    on_interface = own >= 0
                    # A route to another interface's own resolver says nothing
                    # about whether it competes for this primary destination.
                    ambiguous_route = primary and on_interface and any(
                        index != row["index"] and size >= own for index, size in matches
                    )
                except ValueError:
                    errors.append("Windows returned an invalid DNS resolver address.")
            else:
                scope = server.partition("%")[2] or None
            evidence.append(WindowsDNSResolverEvidence(
                row["index"], row["alias"], "IPv4" if row["family"] == 2 else "IPv6",
                server, scope, primary, on_interface,
            ))
            if primary:
                direct.append(server)
                if ambiguous_route:
                    unavailable[server] = "A primary DNS resolver has an ambiguous Windows route."
                elif on_interface is not True:
                    unavailable[server] = "A primary DNS resolver has no verified route on that interface."

    if direct:
        result = dns.check_resolvers(
            _HOSTNAME, direct, compare_public=False, unavailable=unavailable,
        )
    else:
        errors.append("No primary-interface DNS resolver was available for a direct check.")
        result = DNSDiagnosticResult(None, None, None)
    result.system_query = system_query
    result.resolver_evidence = evidence
    result.attribution_error = " ".join(dict.fromkeys([*errors, *unavailable.values()])) or None
    result.likely_dns_issue = (
        result.healthy is False and system_query.success is False and result.measurements_complete
    )
    return result
