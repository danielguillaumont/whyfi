"""Structured models for WHYFI diagnoses."""

from dataclasses import dataclass, field
from enum import StrEnum


class DiagnosisCode(StrEnum):
    """Machine-readable WHYFI diagnosis codes."""

    HEALTHY = "healthy"
    NO_CONNECTION = "no_connection"
    GATEWAY_ISSUE = "gateway_issue"
    INTERNET_ISSUE = "internet_issue"
    DNS_ISSUE = "dns_issue"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class DiagnosisResult:
    """Represents WHYFI's final evidence-backed diagnosis."""

    code: DiagnosisCode
    title: str
    confidence: int
    summary: str
    evidence: list[str] = field(default_factory=list)
    recommendation: str | None = None
