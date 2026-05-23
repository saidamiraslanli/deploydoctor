from typer.testing import CliRunner

from deploydoctor import __version__
from deploydoctor.cli import _normalize_domain, app

runner = CliRunner()


def test_normalize_bare_host():
    assert _normalize_domain("example.com") == "example.com"


def test_normalize_url():
    assert _normalize_domain("https://example.com/foo/bar") == "example.com"


def test_normalize_strips_trailing_dot_and_space():
    assert _normalize_domain("  example.com.  ") == "example.com"


def test_normalize_with_port_returns_host_only():
    # Bare-host fallback: split on first '/' only; explicit URLs use urlparse.
    assert _normalize_domain("https://example.com:8443/api") == "example.com"


def test_version_command():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_help_lists_subcommands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("check", "remote", "local", "version"):
        assert cmd in result.stdout
