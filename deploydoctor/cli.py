"""DeployDoctor command-line interface."""

from __future__ import annotations

import sys
from urllib.parse import urlparse

import typer
from rich.console import Console

from deploydoctor import __version__
from deploydoctor.checks.dns import check_dns
from deploydoctor.checks.http import check_http, check_https
from deploydoctor.checks.local import run_local_checks
from deploydoctor.checks.ports import check_ports
from deploydoctor.checks.ssl_check import check_ssl
from deploydoctor.models import Report
from deploydoctor.utils.formatting import render_report

app = typer.Typer(
    name="deploydoctor",
    help="Diagnose Nginx, SSL, Docker, DNS, ports, and web app deployment problems from one CLI.",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()


def _normalize_domain(domain: str) -> str:
    """Accept either bare host or URL; return host only."""
    domain = domain.strip()
    if "://" in domain:
        parsed = urlparse(domain)
        host = parsed.hostname or ""
    else:
        host = domain.split("/", 1)[0]
    return host.strip().rstrip(".")


def _exit_code(report: Report) -> int:
    if report.failed_count > 0:
        return 2
    if report.warn_count > 0:
        return 1
    return 0


def _run_remote(domain: str, report: Report) -> None:
    report.add(check_dns(domain))
    report.add(check_http(domain))
    report.add(check_https(domain))
    report.add(check_ssl(domain))
    report.add(check_ports(domain))


@app.command()
def check(
    domain: str = typer.Argument(..., help="Domain or URL to diagnose, e.g. example.com"),
) -> None:
    """Run all remote and local checks."""
    host = _normalize_domain(domain)
    if not host:
        console.print("[bold red]Invalid domain[/bold red]")
        raise typer.Exit(code=2)
    report = Report(domain=host)
    _run_remote(host, report)
    for r in run_local_checks():
        report.add(r)
    render_report(console, report)
    sys.exit(_exit_code(report))


@app.command()
def remote(
    domain: str = typer.Argument(..., help="Domain or URL to diagnose"),
) -> None:
    """Run only remote checks (DNS, HTTP, HTTPS, SSL, ports)."""
    host = _normalize_domain(domain)
    if not host:
        console.print("[bold red]Invalid domain[/bold red]")
        raise typer.Exit(code=2)
    report = Report(domain=host)
    _run_remote(host, report)
    render_report(console, report)
    sys.exit(_exit_code(report))


@app.command()
def local() -> None:
    """Run only local server checks."""
    report = Report(domain=None)
    for r in run_local_checks():
        report.add(r)
    render_report(console, report)
    sys.exit(_exit_code(report))


@app.command()
def version() -> None:
    """Print the DeployDoctor version."""
    console.print(f"deploydoctor {__version__}")


if __name__ == "__main__":
    app()
