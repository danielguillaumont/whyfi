"""Command-line entry point for WHYFI."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from whyfi.diagnosis.engine import diagnose_baseline
from whyfi.diagnosis.quality import diagnose_connection_quality
from whyfi.diagnostics.windows.baseline import run_baseline_diagnostics
from whyfi.diagnostics.windows.quality import check_connection_quality
from whyfi.models.diagnosis import DiagnosisResult


def _print_diagnosis(diagnosis: DiagnosisResult) -> None:
    """Display a WHYFI diagnosis in the terminal."""

    print()
    print(diagnosis.title)
    print(f"Confidence: {diagnosis.confidence}%")
    print()
    print(diagnosis.summary)

    if diagnosis.evidence:
        print()
        print("Evidence:")

        for item in diagnosis.evidence:
            print(f"  - {item}")

    if diagnosis.recommendation:
        print()
        print("Recommendation:")
        print(diagnosis.recommendation)

    print()


def _print_technical_details(data: object) -> None:
    """Display structured diagnostic measurements."""

    print("Technical details:")
    print(
        json.dumps(
            asdict(data),
            indent=2,
            default=str,
        )
    )
    print()


def _print_json_result(
    diagnosis: DiagnosisResult,
    details: object,
) -> None:
    """Output a machine-readable WHYFI diagnostic result."""

    payload = {
        "diagnosis": asdict(diagnosis),
        "details": asdict(details),
    }

    print(
        json.dumps(
            payload,
            indent=2,
            default=str,
        )
    )


def _run_baseline() -> DiagnosisResult:
    """Run WHYFI's standard baseline investigation."""

    baseline = run_baseline_diagnostics(
        progress=print,
    )

    return diagnose_baseline(baseline)


def _run_quality() -> DiagnosisResult:
    """Run WHYFI's deeper connection-quality investigation."""

    quality = check_connection_quality(
        sample_count=10,
        progress=print,
    )

    return diagnose_connection_quality(quality)


def main() -> None:
    """Run WHYFI from the command line."""

    parser = argparse.ArgumentParser(
        prog="WHYFI",
        description="Find out why your internet is acting weird.",
    )

    mode = parser.add_mutually_exclusive_group()

    mode.add_argument(
        "--quality",
        action="store_true",
        help="Run a deeper packet-loss and jitter investigation.",
    )

    mode.add_argument(
        "--details",
        action="store_true",
        help="Show the baseline diagnosis and raw technical measurements.",
    )

    mode.add_argument(
        "--json",
        action="store_true",
        help="Output the baseline diagnosis as machine-readable JSON.",
    )

    args = parser.parse_args()

    if args.json:
        baseline = run_baseline_diagnostics()
        diagnosis = diagnose_baseline(baseline)

        _print_json_result(
            diagnosis,
            baseline,
        )
        return

    print()
    print("WHYFI")
    print("=" * 50)

    if args.quality:
        print("Running deeper connection-quality analysis...")
        diagnosis = _run_quality()
        _print_diagnosis(diagnosis)
        return

    if args.details:
        print("Investigating your network...")
        baseline = run_baseline_diagnostics()
        diagnosis = diagnose_baseline(baseline)

        _print_diagnosis(diagnosis)
        _print_technical_details(baseline)
        return

    print("Investigating your network...")
    diagnosis = _run_baseline()
    _print_diagnosis(diagnosis)


if __name__ == "__main__":
    main()
