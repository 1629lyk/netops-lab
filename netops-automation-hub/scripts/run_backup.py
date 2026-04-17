#!/usr/bin/env python3
"""
run_backup.py — Run config backup against all devices.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from rich.console import Console
from rich.table import Table
from src.core.engine import get_nornir_managed
from src.tasks.backup import backup_config
from src.database.session import init_db

console = Console()


def main():
    console.print("\n[bold cyan]NetOps Automation Hub — Config Backup[/bold cyan]\n")

    # Ensure tables exist
    init_db()

    nr = get_nornir_managed()
    results = nr.run(task=backup_config)

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Host",    style="cyan", width=12)
    table.add_column("Status",  width=8)
    table.add_column("Lines",   width=8)
    table.add_column("File",    style="dim")

    all_pass = True
    for host, result in results.items():
        if result.failed:
            table.add_row(host, "[red]FAIL[/red]", "-", str(result.exception))
            all_pass = False
        else:
            data = result[0].result
            status = "[green]OK[/green]" if data["success"] else "[red]FAIL[/red]"
            table.add_row(
                host,
                status,
                str(data["lines"]),
                data["filepath"]
            )
            if not data["success"]:
                all_pass = False

    console.print(table)

    if all_pass:
        console.print("\n[bold green]All backups complete.[/bold green]\n")
    else:
        console.print("\n[bold red]One or more backups failed.[/bold red]\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
