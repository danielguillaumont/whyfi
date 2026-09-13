"""Direct-IP internet reachability checks for WHYFI."""

from __future__ import annotations

from whyfi.diagnostics.windows.ping import ping_host
from whyfi.models.probes import InternetReachabilityResult


_DEFAULT_TARGETS = (
    "1.1.1.1",
    "8.8.8.8",
)


def check_internet_reachability(
    targets: tuple[str, ...] = _DEFAULT_TARGETS,
) -> InternetReachabilityResult:
    """Check whether the system can reach the wider internet by IP address."""

    probes = [ping_host(target) for target in targets]

    targets_reachable = sum(1 for probe in probes if probe.reachable)

    return InternetReachabilityResult(
        reachable=targets_reachable > 0,
        targets_tested=len(probes),
        targets_reachable=targets_reachable,
        probes=probes,
        error=None if targets_reachable > 0 else "No public IP targets responded.",
    )
