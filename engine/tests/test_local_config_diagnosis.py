"""Local configuration diagnosis tests for WHYFI."""

from whyfi.diagnosis.engine import diagnose_baseline
from whyfi.models.diagnostic import BaselineDiagnosticResult
from whyfi.models.diagnosis import DiagnosisCode
from whyfi.models.local_config import LocalConfigResult


def test_dhcp_failure_beats_no_connection() -> None:
    """APIPA should be diagnosed before generic no-connection."""

    local_config = LocalConfigResult(
        healthy=False,
        active_adapters=["Wi-Fi"],
        usable_ipv4_adapters=[],
        link_local_ipv4_adapters=["Wi-Fi"],
        likely_dhcp_issue=True,
        error=(
            "An active adapter has only a link-local IPv4 address. "
            "DHCP may have failed."
        ),
    )

    baseline = BaselineDiagnosticResult(
        connection=None,
        gateway=None,
        internet=None,
        dns=None,
        wifi=None,
        local_config=local_config,
        completed=False,
        error="No primary network connection was found.",
    )

    diagnosis = diagnose_baseline(baseline)

    assert diagnosis.code == DiagnosisCode.LOCAL_CONFIG_ISSUE
    assert diagnosis.confidence >= 90
    assert "169.254" in diagnosis.summary


def test_no_adapter_remains_no_connection() -> None:
    """No active adapter should remain a generic no-connection diagnosis."""

    local_config = LocalConfigResult(
        healthy=False,
        active_adapters=[],
        usable_ipv4_adapters=[],
        link_local_ipv4_adapters=[],
        likely_dhcp_issue=False,
        error="No active physical network adapters were found.",
    )

    baseline = BaselineDiagnosticResult(
        connection=None,
        gateway=None,
        internet=None,
        dns=None,
        wifi=None,
        local_config=local_config,
        completed=False,
        error="No primary network connection was found.",
    )

    diagnosis = diagnose_baseline(baseline)

    assert diagnosis.code == DiagnosisCode.NO_CONNECTION
