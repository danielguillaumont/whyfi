"""DNS diagnostics for WHYFI."""

from __future__ import annotations

import time

import dns.exception
import dns.resolver

from whyfi.models.dns import DNSDiagnosticResult, DNSQueryResult


_ALTERNATE_RESOLVERS = (
    "1.1.1.1",
    "8.8.8.8",
)


def get_system_dns_servers() -> list[str]:
    """Return DNS servers configured on the local system."""

    resolver = dns.resolver.Resolver(configure=True)

    return [str(server) for server in resolver.nameservers]


def query_dns(
    hostname: str,
    resolver_address: str,
    timeout: float = 2.0,
) -> DNSQueryResult:
    """Resolve an IPv4 hostname using one specific DNS resolver."""

    resolver = dns.resolver.Resolver(configure=False)
    resolver.nameservers = [resolver_address]
    resolver.timeout = timeout
    resolver.lifetime = timeout

    start = time.perf_counter()

    try:
        answer = resolver.resolve(hostname, "A")

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

    except dns.resolver.NoNameservers:
        return DNSQueryResult(
            hostname=hostname,
            resolver=resolver_address,
            success=False,
            error="Resolver has no usable nameservers.",
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
            success=False,
            error=str(exc),
        )


def check_dns(
    hostname: str = "example.com",
) -> DNSDiagnosticResult:
    """Compare the configured DNS resolver with known public resolvers."""

    system_resolvers = get_system_dns_servers()

    if not system_resolvers:
        return DNSDiagnosticResult(
            healthy=False,
            default_resolver=None,
            default_query=None,
            likely_dns_issue=True,
            error="No configured DNS resolver was found.",
        )

    default_resolver = system_resolvers[0]

    default_query = query_dns(
        hostname=hostname,
        resolver_address=default_resolver,
    )

    alternate_queries = [
        query_dns(
            hostname=hostname,
            resolver_address=resolver,
        )
        for resolver in _ALTERNATE_RESOLVERS
        if resolver != default_resolver
    ]

    alternate_success = any(
        query.success for query in alternate_queries
    )

    likely_dns_issue = (
        not default_query.success
        and alternate_success
    )

    return DNSDiagnosticResult(
        healthy=default_query.success,
        default_resolver=default_resolver,
        default_query=default_query,
        alternate_queries=alternate_queries,
        likely_dns_issue=likely_dns_issue,
        error=None,
    )
