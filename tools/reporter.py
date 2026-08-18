"""
tools/reporter.py - Rich terminal reporter for step-by-step agent status.
Displays a live, colored table of each workflow step with its result.
Windows-safe: forces UTF-8 output and uses ASCII-safe icons as fallback.
"""

import sys
import io
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from datetime import datetime

# Force UTF-8 output on Windows to handle emoji/unicode characters
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

console = Console(file=sys.stdout, force_terminal=True, emoji=True)


class StepResult:
    """Holds the outcome of a single agent step."""

    def __init__(self, step: str, success: bool, detail: str = "", extra: dict = None):
        self.step = step
        self.success = success
        self.detail = detail
        self.extra = extra or {}
        self.timestamp = datetime.now().strftime("%H:%M:%S")


class Reporter:
    """Collects step results and renders a final summary table."""

    def __init__(self, title: str = "AI Agent Workflow"):
        self.title = title
        self.results: list[StepResult] = []

    # ── Live printing ──────────────────────────────────────────────────────────
    def start(self, prompt: str):
        console.print()
        console.print(
            Panel(
                f"[bold cyan]Prompt:[/bold cyan] [italic]{prompt}[/italic]",
                title=f"[bold magenta]AI {self.title}[/bold magenta]",
                border_style="magenta",
            )
        )
        console.print()

    def step_start(self, step_name: str):
        console.print(f"  [bold yellow]  Running:[/bold yellow] {step_name} ...", end="\r")

    def step_done(self, result: StepResult):
        self.results.append(result)
        icon  = "[OK]" if result.success else "[FAIL]"
        color = "green" if result.success else "red"
        detail_str = f"  -> {result.detail}" if result.detail else ""
        console.print(
            f"  [{color}]{icon} {result.step}[/{color}]{detail_str}"
        )

    # ── Final summary table ────────────────────────────────────────────────────
    def summary(self):
        console.print()
        table = Table(
            title="Workflow Summary",
            box=box.ROUNDED,
            border_style="cyan",
            show_lines=True,
            title_style="bold cyan",
        )
        table.add_column("Step", style="bold white", no_wrap=True)
        table.add_column("Status", justify="center", no_wrap=True)
        table.add_column("Detail", style="dim")
        table.add_column("Time", style="dim", no_wrap=True)

        all_ok = True
        for r in self.results:
            status = "[green]SUCCESS[/green]" if r.success else "[red]FAILED[/red]"
            if not r.success:
                all_ok = False
            table.add_row(r.step, status, r.detail or "-", r.timestamp)

        console.print(table)

        # Extra details (URLs, file paths)
        for r in self.results:
            for key, val in r.extra.items():
                console.print(f"  [bold cyan]{key}:[/bold cyan] [underline]{val}[/underline]")

        console.print()
        if all_ok:
            console.print(
                Panel(
                    "[bold green]All steps completed successfully![/bold green]",
                    border_style="green",
                )
            )
        else:
            console.print(
                Panel(
                    "[bold red]Some steps failed. Check details above.[/bold red]",
                    border_style="red",
                )
            )
        console.print()
