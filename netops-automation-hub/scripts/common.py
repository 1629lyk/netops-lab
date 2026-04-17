import os
import time
from dotenv import load_dotenv
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException
from rich.console import Console
from rich.table import Table

load_dotenv()
console = Console()

# ── Credentials ────────────────────────────────────────────────────────────────
FRR_USER    = os.getenv("FRR_USERNAME")
FRR_PASS    = os.getenv("FRR_PASSWORD")
CISCO_USER  = os.getenv("CISCO_USERNAME")
CISCO_PASS  = os.getenv("CISCO_PASSWORD")
CISCO_EN    = os.getenv("CISCO_ENABLE")
ASA_USER    = os.getenv("ASA_USERNAME")
ASA_PASS    = os.getenv("ASA_PASSWORD")
ASA_EN      = os.getenv("ASA_ENABLE")

# ── Device IPs ─────────────────────────────────────────────────────────────────
FRR_R1_HOST = os.getenv("FRR_R1_HOST")
FRR_R2_HOST = os.getenv("FRR_R2_HOST")
ASA_HOST    = os.getenv("ASA_HOST")
SW2_HOST    = os.getenv("SW2_HOST")
SW1_HOST    = os.getenv("SW1_HOST")
PC1_HOST    = os.getenv("PC1_HOST")
PC2_HOST    = os.getenv("PC2_HOST")
PC_USER  = os.getenv("PC_USERNAME")
PC1_PASS = os.getenv("PC1_PASSWORD")
PC2_PASS = os.getenv("PC2_PASSWORD")

# ── Shared results store ───────────────────────────────────────────────────────
results = {}


def connect(host, username, password, device_type="linux",
            timeout=30, secret=None):
    device = {
        "device_type": device_type,
        "host":        host,
        "username":    username,
        "password":    password,
        "timeout":     timeout,
        "fast_cli":    False,
    }
    if secret:
        device["secret"] = secret

    # ASA requires legacy SSH algorithms
    if device_type == "cisco_asa":
        device["conn_timeout"]   = 60
        device["banner_timeout"] = 60

    try:
        conn = ConnectHandler(**device)
        if secret:
            conn.enable()
        return conn
    except NetmikoAuthenticationException:
        console.print(f"  [red]AUTH FAILED[/red] — {host}")
        return None
    except NetmikoTimeoutException:
        console.print(f"  [red]TIMEOUT[/red] — {host} unreachable")
        return None
    except Exception as e:
        console.print(f"  [red]ERROR[/red] — {host}: {e}")
        return None


def run(conn, cmd):
    """Run a command and return output."""
    return conn.send_command(cmd, expect_string=r"\$|#|>").strip()


def run_config(conn, cmd):
    """Fire-and-forget command, no prompt matching."""
    return conn.send_command_timing(
        cmd, strip_prompt=False, strip_command=False
    )


def section(title):
    console.rule(f"[bold cyan]{title}[/bold cyan]")


def ok(msg):
    console.print(f"  [green]✔[/green]  {msg}")


def warn(msg):
    console.print(f"  [yellow]⚠[/yellow]  {msg}")


def fail(msg):
    console.print(f"  [red]✘[/red]  {msg}")


def print_status(results):
    section("Bootstrap Status")
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Device", style="bold", width=12)
    table.add_column("Status", width=8)
    table.add_column("Notes",  width=45)

    colors = {"PASS": "green", "FAIL": "red", "SKIP": "yellow"}
    for device, info in results.items():
        color = colors.get(info["status"], "white")
        table.add_row(
            device,
            f"[{color}]{info['status']}[/{color}]",
            info["notes"]
        )
    console.print(table)
