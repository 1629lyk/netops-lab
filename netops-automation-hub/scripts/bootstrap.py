#!/usr/bin/env python3
"""
NetOps Automation Hub — Bootstrap Master
Usage: python3 scripts/bootstrap.py
"""

import sys
import os

# Allow imports from scripts/ directory
sys.path.insert(0, os.path.dirname(__file__))

from common import console, results, print_status
from bootstrap import frr_r2, frr_r1, asa_fw, sw2_l3, sw1_l2, pc1, pc2


MENU = {
    "1": ("FRR-R2  — ISP router",          frr_r2.bootstrap),
    "2": ("FRR-R1  — Edge router",          frr_r1.bootstrap),
    "3": ("SW2-L3  — Distribution switch",  sw2_l3.bootstrap),
    "4": ("SW1-L2  — Access switch",        sw1_l2.bootstrap),
    "5": ("PC1     — VLAN10 endpoint",      pc1.bootstrap),
    "6": ("PC2     — VLAN20 endpoint",      pc2.bootstrap),
    "*": ("ALL     — Bootstrap full lab",   None),
    "0": ("QUIT",                           None),
}


def print_menu():
    console.print("\n[bold cyan]NetOps Automation Hub — Lab Bootstrap[/bold cyan]")
    console.print("─" * 50)
    for key,(label, _) in MENU.items():
        console.print(f"  [{str(key)}]  {label}")
    console.print("─" * 50)


def run_all():
    """Bootstrap all nodes in dependency order."""
    order = ["1", "2", "3", "4", "5", "6"]
    for key in order:
        _, func = MENU[key]
        func(results)
    print_status(results)


def main():
    while True:
        print_menu()
        choice = input("\n  Select option: ").strip().lower()

        if choice == "0":
            console.print("[yellow]Exiting.[/yellow]")
            sys.exit(0)

        elif choice == "*":
            run_all()

        elif choice in MENU:
            label, func = MENU[choice]
            console.print(f"\n[bold]Running: {label}[/bold]")
            func(results)
            print_status(results)

        else:
            console.print("[red]Invalid option — try again.[/red]")


if __name__ == "__main__":
    main()
