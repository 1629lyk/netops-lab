#!/usr/bin/env python3
"""
run_compliance.py — Run compliance checks against all devices.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from rich.console import Console
from rich.table import Table
from src.core.engine import get_nornir_managed
from src.tasks.compliance import check_compliance
from src.database.session import init_db

console = Console()


def main():
    console.print("\n[bold cyan]NetOps Automation Hub — Compliance Check[/bold cyan]\n")

    init_db()

    nr = get_nornir_managed()
    results = nr.run(task=check_compliance)

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Host",    style="cyan", width=12)
    table.add_column("Policy",  width=28)
    table.add_column("Status",  width=8)
    table.add_column("Detail",  style="dim")

    all_pass = True
    for host, result in results.items():
        if result.failed:
            table.add_row(host, "-", "[red]FAIL[/red]", str(result.exception))
            all_pass = False
        else:
            policy_results = result[0].result
            for r in policy_results:
                status = "[green]PASS[/green]" if r["passed"] else "[red]FAIL[/red]"
                table.add_row(
                    host,
                    r["policy"],
                    status,
                    r["detail"]
                )
                if not r["passed"]:
                    all_pass = False

    console.print(table)

    if all_pass:
        console.print("\n[bold green]All compliance checks passed.[/bold green]\n")
    else:
        console.print("\n[bold yellow]Some checks failed — review details above.[/bold yellow]\n")


if __name__ == "__main__":
    main()
