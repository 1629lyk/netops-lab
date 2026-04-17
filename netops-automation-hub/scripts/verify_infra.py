#!/usr/bin/env python3
"""
verify_infra.py — Stage 2 infrastructure check
Verifies PostgreSQL and Redis are reachable from Python.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
import os

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

console = Console()

def check_postgres():
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=os.getenv("DB_PORT", 5432),
            dbname=os.getenv("DB_NAME", "netops_hub"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            connect_timeout=5
        )
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()[0].split(",")[0]
        conn.close()
        return True, version
    except Exception as e:
        return False, str(e)

def check_redis():
    try:
        import redis
        r = redis.Redis(
            host="127.0.0.1",
            port=6379,
            socket_connect_timeout=5
        )
        r.ping()
        info = r.info("server")
        version = info.get("redis_version", "unknown")
        return True, f"Redis {version}"
    except Exception as e:
        return False, str(e)

def main():
    console.print("\n[bold cyan]NetOps Automation Hub — Infrastructure Check[/bold cyan]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Service", style="cyan", width=16)
    table.add_column("Status", width=10)
    table.add_column("Detail", style="dim")

    checks = [
        ("PostgreSQL", check_postgres),
        ("Redis",      check_redis),
    ]

    all_pass = True
    for name, fn in checks:
        ok, detail = fn()
        status = "[green]PASS[/green]" if ok else "[red]FAIL[/red]"
        table.add_row(name, status, detail)
        if not ok:
            all_pass = False

    console.print(table)

    if all_pass:
        console.print("\n[bold green]All checks passed. Stage 2 complete.[/bold green]\n")
    else:
        console.print("\n[bold red]One or more checks failed. See detail above.[/bold red]\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
