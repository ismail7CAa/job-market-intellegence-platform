"""Tests for the source registry operator CLI."""

from src.data_pipeline.sources import main


def test_source_registry_cli_prints_blocked_source(capsys):
    """CLI should let operators inspect why a source is blocked."""
    exit_code = main(["--source", "stepstone"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "stepstone" in output
    assert "blocked" in output
    assert "official partner/API access" in output


def test_source_registry_cli_supports_json_output(capsys):
    """Machine-readable source status should be available for automation."""
    exit_code = main(["--source", "company_feed", "--format", "json"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert '"source": "company_feed"' in output
    assert '"allowed": true' in output
