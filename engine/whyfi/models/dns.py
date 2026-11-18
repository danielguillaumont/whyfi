"""Structured models for WHYFI DNS diagnostics."""

from dataclasses import dataclass, field


@dataclass(slots=True)
class DNSQueryResult:
    """Represents the result of a single DNS query."""

    hostname: str
    resolver: str
    success: bool | None
    latency_ms: float | None = None
    addresses: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass(slots=True)
class DNSDiagnosticResult:
    """Represents WHYFI's comparison of DNS resolvers."""

    healthy: bool | None
    default_resolver: str | None
    default_query: DNSQueryResult | None
    alternate_queries: list[DNSQueryResult] = field(default_factory=list)
    likely_dns_issue: bool = False
    error: str | None = None
    configured_queries: list[DNSQueryResult] = field(default_factory=list)

    @property
    def measurements_complete(self) -> bool:
        """Whether configured resolver evidence is available for assessment."""
        queries = self.configured_queries or ([self.default_query] if self.default_query else [])
        return self.healthy is not None and all(query.success is not None for query in queries)
