#!/usr/bin/env python3
"""
test_connectivity.py — Stage 3 connectivity check
Verifies Nornir can SSH into all 5 devices and run a basic command.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from nornir_netmiko.tasks import netmiko_send_command
from nornir.core.filter import F
from rich.console import Console
from rich.table import Table
from src.core.engine import get_nornir_managed

console = Console()

# Simple command per platform to verify connectivity
PLATFORM_COMMANDS = {
    "linux": "uname -n",
    "ios":   "show version | include Version",
    "asa":   "show version | include Version",
}

def test_connectivity(task):
    platform = task.host.platform
    cmd = PLATFORM_COMMANDS.get(platform, "show version")
    result = task.run(
        task=netmiko_send_command,
        command_string=cmd,
        use_timing=True
    )
    return result[0].result


def main():
    console.print("\n[bold cyan]NetOps Automation Hub — Connectivity Check[/bold cyan]\n")

    nr = get_nornir_managed()
    results = nr.run(task=test_connectivity)

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Host",     style="cyan", width=12)
    table.add_column("Platform", width=12)
    table.add_column("Status",   width=8)
    table.add_column("Output",   style="dim")

    all_pass = True
    for host, result in results.items():
        platform = nr.inventory.hosts[host].platform
        if result.failed:
            status = "[red]FAIL[/red]"
            output = str(result.exception)
            all_pass = False
        else:
            status = "[green]PASS[/green]"
            output = result[0].result.strip().splitlines()[0][:60]
        table.add_row(host, platform, status, output)

    console.print(table)

    if all_pass:
        console.print("\n[bold green]All devices reachable. Stage 3 complete.[/bold green]\n")
    else:
        console.print("\n[bold red]One or more devices failed. Check output above.[/bold red]\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
