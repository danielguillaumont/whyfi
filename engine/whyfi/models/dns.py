"""Structured models for WHYFI DNS diagnostics."""

from dataclasses import dataclass, field


@dataclass(slots=True)
class DNSQueryResult:
    """Represents the result of a single DNS query."""

    hostname: str
    resolver: str
    success: bool
    latency_ms: float | None = None
    addresses: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass(slots=True)
class DNSDiagnosticResult:
    """Represents WHYFI's comparison of DNS resolvers."""

    healthy: bool
    default_resolver: str | None
    default_query: DNSQueryResult | None
    alternate_queries: list[DNSQueryResult] = field(default_factory=list)
    likely_dns_issue: bool = False
    error: str | None = None
