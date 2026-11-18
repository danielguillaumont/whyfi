"""DNS diagnostics for WHYFI."""

from __future__ import annotations

import ipaddress
import json
import subprocess
import sys
import time

import dns.exception
import dns.resolver

from whyfi.models.dns import DNSDiagnosticResult, DNSQueryResult


_ALTERNATE_RESOLVERS = (
    "1.1.1.1",
    "8.8.8.8",
)
_PUBLIC_TEST_HOST = "example.com"


def get_system_dns_servers(primary_interface_index: int | None = None) -> list[str]:
    """Return configured DNS servers, preferring the primary Windows interface."""

    if sys.platform != "win32":
        resolver = dns.resolver.Resolver(configure=True)
        return [str(server) for server in resolver.nameservers]

    script = """
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$interfaces = @(Get-NetIPInterface)
if ($interfaces.Count -eq 0) { throw 'Windows returned no IP interface inventory.' }
$dnsByInterface = @{}
Get-DnsClientServerAddress | ForEach-Object {
    $key = "$($_.InterfaceIndex):$([int]$_.AddressFamily)"
    $dnsByInterface[$key] = $_
}
$rows = @($interfaces | Where-Object ConnectionState -eq 'Connected' | ForEach-Object {
    $key = "$($_.InterfaceIndex):$([int]$_.AddressFamily)"
    if (-not $dnsByInterface.ContainsKey($key) -or
        $null -eq $dnsByInterface[$key].PSObject.Properties['ServerAddresses']) {
        throw "Windows returned no DNS configuration record for interface $key."
    }
    $addresses = $dnsByInterface[$key].ServerAddresses
    if ($null -eq $addresses) { $addresses = @() }
    [PSCustomObject]@{
        index = $_.InterfaceIndex
        family = [int]$_.AddressFamily
        metric = $_.InterfaceMetric
        servers = @($addresses)
    }
})
ConvertTo-Json -InputObject $rows -Compress
"""
    try:
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=10,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Windows DNS configuration lookup timed out.") from exc

    if completed.returncode != 0 or completed.stderr.strip():
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(
            f"Windows DNS configuration lookup failed (exit {completed.returncode}): {detail}"
        )

    rows = json.loads(completed.stdout)
    if not isinstance(rows, list) or any(
        not isinstance(row, dict)
        or any(type(row.get(key)) is not int for key in ("index", "family", "metric"))
        or not isinstance(row.get("servers"), list)
        or any(not isinstance(server, str) for server in row["servers"])
        for row in rows
    ):
        raise ValueError("Unrecognized Windows DNS configuration output.")
    if primary_interface_index is not None and not any(
        row["index"] == primary_interface_index for row in rows
    ):
        raise ValueError("Windows DNS inventory did not include the primary interface.")

    servers = []
    for row in sorted(rows, key=lambda row: (
        row["index"] != primary_interface_index, row["metric"], row["index"], row["family"]
    )):
        for server in row["servers"]:
            try:
                address = ipaddress.ip_address(server)
            except ValueError:
                servers.append(server)
                continue
            if (
                isinstance(address, ipaddress.IPv6Address)
                and address.is_link_local
                and not address.scope_id
            ):
                server = f"{address}%{row['index']}"
            servers.append(server)
    return servers


def query_dns(
    hostname: str,
    resolver_address: str,
    timeout: float = 2.0,
) -> DNSQueryResult:
    """Resolve an IPv4 hostname using one specific DNS resolver."""

    start = time.perf_counter()

    try:
        resolver = dns.resolver.Resolver(configure=False)
        resolver.nameservers = [resolver_address]
        resolver.timeout = timeout
        resolver.lifetime = timeout
        answer = resolver.resolve(hostname, "A", search=False)

        latency_ms = round(
            (time.perf_counter() - start) * 1000,
            2,
        )

        addresses = [record.address for record in answer]

        return DNSQueryResult(
            hostname=hostname,
            resolver=resolver_address,
            success=True,
            latency_ms=latency_ms,
            addresses=addresses,
        )

    except dns.resolver.NXDOMAIN:
        return DNSQueryResult(
            hostname=hostname,
            resolver=resolver_address,
            success=False,
            error="Hostname does not exist.",
        )

    except dns.resolver.NoAnswer:
        return DNSQueryResult(
            hostname=hostname,
            resolver=resolver_address,
            success=False,
            error="Resolver returned no A record.",
        )

    except dns.resolver.NoNameservers as exc:
        # dnspython groups resolver replies and local transport errors here.
        # Only a DNS response establishes a failed lookup.
        received_response = any(
            error[-1] is not None for error in exc.kwargs.get("errors", ())
        )
        return DNSQueryResult(
            hostname=hostname,
            resolver=resolver_address,
            success=False if received_response else None,
            error=str(exc),
        )

    except dns.exception.Timeout:
        return DNSQueryResult(
            hostname=hostname,
            resolver=resolver_address,
            success=False,
            error="DNS query timed out.",
        )

    except Exception as exc:
        return DNSQueryResult(
            hostname=hostname,
            resolver=resolver_address,
            success=None,
            error=f"DNS query could not be measured: {exc}",
        )


def _resolver_key(address: str) -> str:
    try:
        return str(ipaddress.ip_address(address))
    except ValueError:
        return address


def check_dns(
    hostname: str = _PUBLIC_TEST_HOST,
    *,
    primary_interface_index: int | None = None,
) -> DNSDiagnosticResult:
    """Assess each configured resolver and optionally compare a public lookup."""

    try:
        system_resolvers = get_system_dns_servers(primary_interface_index)
    except Exception as exc:
        return DNSDiagnosticResult(
            healthy=None,
            default_resolver=None,
            default_query=None,
            error=f"Could not discover configured DNS resolvers: {exc}",
        )

    resolver_addresses = {}
    for address in system_resolvers:
        resolver_addresses.setdefault(_resolver_key(address), address)
    configured_queries = [
        query_dns(hostname=hostname, resolver_address=address)
        for address in resolver_addresses.values()
    ]
    default_query = configured_queries[0] if configured_queries else None
    if any(query.success is True for query in configured_queries):
        healthy = True
        error = None
    elif any(query.success is None for query in configured_queries):
        healthy = None
        error = "Configured DNS resolution could not be determined."
    else:
        healthy = False
        error = (
            "No configured resolver answered the test lookup successfully."
            if configured_queries else "No configured DNS resolver was found."
        )

    alternate_queries = []
    if configured_queries and healthy is False and hostname.casefold().rstrip(".") == _PUBLIC_TEST_HOST:
        alternate_queries = [
            query_dns(hostname=hostname, resolver_address=resolver)
            for resolver in _ALTERNATE_RESOLVERS
            if resolver not in resolver_addresses
        ]

    return DNSDiagnosticResult(
        healthy=healthy,
        default_resolver=default_query.resolver if default_query else None,
        default_query=default_query,
        alternate_queries=alternate_queries,
        likely_dns_issue=healthy is False,
        error=error,
        configured_queries=configured_queries,
    )
