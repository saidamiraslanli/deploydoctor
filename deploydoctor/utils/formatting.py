"""Rich rendering for CheckResult / Report."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from deploydoctor.models import CheckResult, Report, Status

STATUS_STYLES: dict[Status, tuple[str, str]] = {
    Status.PASS: ("PASS", "bold green"),
    Status.WARN: ("WARN", "bold yellow"),
    Status.FAIL: ("FAIL", "bold red"),
    Status.SKIP: ("SKIP", "dim"),
}


def status_text(status: Status) -> Text:
    label, style = STATUS_STYLES[status]
    return Text(label, style=style)


def render_result(console: Console, result: CheckResult) -> None:
    body = Table.grid(padding=(0, 1))
    body.add_column(no_wrap=True)
    body.add_column(overflow="fold")
    body.add_row(status_text(result.status), Text(result.message or "", style="white"))
    if result.details:
        details_table = Table.grid(padding=(0, 1))
        details_table.add_column(no_wrap=True, style="dim")
        details_table.add_column(overflow="fold")
        for d in result.details:
            details_table.add_row("•", d)
        body.add_row("", details_table)
    if result.suggestions:
        sug_table = Table.grid(padding=(0, 1))
        sug_table.add_column(no_wrap=True, style="cyan")
        sug_table.add_column(overflow="fold")
        for s in result.suggestions:
            sug_table.add_row("→", s)
        body.add_row("", sug_table)
    console.print(Panel(body, title=f"[bold]{result.name}[/bold]", border_style=_panel_style(result.status)))


def _panel_style(status: Status) -> str:
    return {
        Status.PASS: "green",
        Status.WARN: "yellow",
        Status.FAIL: "red",
        Status.SKIP: "grey50",
    }[status]


def render_report(console: Console, report: Report) -> None:
    title = "DeployDoctor Report"
    if report.domain:
        title = f"DeployDoctor Report for {report.domain}"
    console.rule(f"[bold cyan]{title}[/bold cyan]")
    for r in report.results:
        render_result(console, r)
    summary = Table(show_header=True, header_style="bold magenta", title="Summary")
    summary.add_column("Passed", justify="right", style="green")
    summary.add_column("Warnings", justify="right", style="yellow")
    summary.add_column("Failed", justify="right", style="red")
    summary.add_column("Skipped", justify="right", style="dim")
    summary.add_row(
        str(report.passed_count),
        str(report.warn_count),
        str(report.failed_count),
        str(report.skipped_count),
    )
    console.print(summary)
    if report.most_likely_issue:
        console.print(Panel(report.most_likely_issue, title="Most likely issue", border_style="red"))
    if report.next_commands:
        nxt = Table.grid(padding=(0, 1))
        nxt.add_column(style="cyan", no_wrap=True)
        nxt.add_column(overflow="fold")
        for c in report.next_commands:
            nxt.add_row("$", c)
        console.print(Panel(nxt, title="Suggested next commands", border_style="cyan"))
