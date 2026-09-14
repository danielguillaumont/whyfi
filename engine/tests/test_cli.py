"""Command-line interface tests for WHYFI."""

import sys

from whyfi import __main__ as cli
from whyfi.models.diagnosis import DiagnosisCode, DiagnosisResult


def make_diagnosis() -> DiagnosisResult:
    """Create a representative diagnosis for CLI tests."""

    return DiagnosisResult(
        code=DiagnosisCode.HEALTHY,
        title="Everything looks healthy.",
        confidence=96,
        summary="Your network is responding normally.",
        evidence=[
            "Gateway reachable.",
            "DNS resolution successful.",
        ],
        recommendation="No action is needed.",
    )


def test_default_cli_runs_baseline(monkeypatch, capsys) -> None:
    """The default command should run the baseline investigation."""

    diagnosis = make_diagnosis()

    monkeypatch.setattr(
        cli,
        "_run_baseline",
        lambda: diagnosis,
    )

    def fail_quality() -> DiagnosisResult:
        raise AssertionError("Quality mode should not run.")

    monkeypatch.setattr(
        cli,
        "_run_quality",
        fail_quality,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        ["whyfi"],
    )

    cli.main()

    output = capsys.readouterr().out

    assert "Investigating your network..." in output
    assert "Everything looks healthy." in output
    assert "Confidence: 96%" in output


def test_quality_flag_runs_quality_mode(monkeypatch, capsys) -> None:
    """The --quality flag should run the deeper investigation."""

    diagnosis = make_diagnosis()

    monkeypatch.setattr(
        cli,
        "_run_quality",
        lambda: diagnosis,
    )

    def fail_baseline() -> DiagnosisResult:
        raise AssertionError("Baseline mode should not run.")

    monkeypatch.setattr(
        cli,
        "_run_baseline",
        fail_baseline,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        ["whyfi", "--quality"],
    )

    cli.main()

    output = capsys.readouterr().out

    assert "Running deeper connection-quality analysis..." in output
    assert "Everything looks healthy." in output


def test_cli_prints_evidence_and_recommendation(capsys) -> None:
    """CLI output should include useful evidence and next steps."""

    cli._print_diagnosis(make_diagnosis())

    output = capsys.readouterr().out

    assert "Evidence:" in output
    assert "Gateway reachable." in output
    assert "DNS resolution successful." in output
    assert "Recommendation:" in output
    assert "No action is needed." in output
