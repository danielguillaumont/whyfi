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
class SystemDNSQueryResult:
    hostname: str
    success: bool | None
    addresses: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass(slots=True)
class WindowsDNSResolverEvidence:
    interface_index: int
    interface_alias: str
    address_family: str
    resolver: str
    scope: str | None
    primary: bool
    route_on_interface: bool | None
    provenance: str = "unknown"


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
    system_query: SystemDNSQueryResult | None = None
    resolver_evidence: list[WindowsDNSResolverEvidence] = field(default_factory=list)
    attribution_error: str | None = None

    @property
    def measurements_complete(self) -> bool:
        """Whether configured resolver evidence is available for assessment."""
        queries = self.configured_queries or ([self.default_query] if self.default_query else [])
        return (
            self.attribution_error is None
            and (self.system_query is None or self.system_query.success is not None)
            and self.healthy is not None
            and all(query.success is not None for query in queries)
        )
