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

    targets_reachable = sum(probe.reachable is True for probe in probes)
    targets_tested = sum(probe.reachable is not None for probe in probes)
    if targets_reachable:
        reachable = True
        error = None
    elif targets_tested == len(targets) and targets_tested:
        reachable = False
        error = "No public IP targets responded."
    else:
        reachable = None
        error = "Public IP reachability could not be determined."

    return InternetReachabilityResult(
        reachable=reachable,
        targets_tested=targets_tested,
        targets_reachable=targets_reachable,
        probes=probes,
        error=error,
    )
