"""
engine.py — Nornir initialization and credential injection
Loads inventory from YAML files, injects credentials from .env at runtime.
"""

import os
from nornir import InitNornir
from nornir.core import Nornir
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

# Credentials from .env
FRR_USERNAME = os.getenv("FRR_USERNAME")
FRR_PASSWORD = os.getenv("FRR_PASSWORD")
CISCO_USERNAME = os.getenv("CISCO_USERNAME")
CISCO_PASSWORD = os.getenv("CISCO_PASSWORD")
CISCO_ENABLE = os.getenv("CISCO_ENABLE")
ASA_USERNAME = os.getenv("ASA_USERNAME")
ASA_PASSWORD = os.getenv("ASA_PASSWORD")
ASA_ENABLE = os.getenv("ASA_ENABLE")

def _inject_credentials(host):
    """Inject credentials into each host based on its group membership."""
    # Ensure netmiko connection_options exists
    if "netmiko" not in host.connection_options:
        from nornir.core.inventory import ConnectionOptions
        host.connection_options["netmiko"] = ConnectionOptions(
            hostname=None, port=None, username=None,
            password=None, platform=None, extras={}
        )

    if "frr" in host.groups:
        host.username = FRR_USERNAME
        host.password = FRR_PASSWORD

    elif "cisco_asa" in host.groups:
        host.username = ASA_USERNAME
        host.password = ASA_PASSWORD
        host.connection_options["netmiko"].extras["secret"] = ASA_ENABLE

    elif "cisco_ios" in host.groups:
        host.username = CISCO_USERNAME
        host.password = CISCO_PASSWORD
        host.connection_options["netmiko"].extras["secret"] = CISCO_ENABLE


def get_nornir() -> Nornir:
    """Initialize and return a Nornir instance with credentials injected."""
    base_dir = os.path.join(os.path.dirname(__file__), '..', '..')

    nr = InitNornir(
        runner={
            "plugin": "threaded",
            "options": {"num_workers": 5}
        },
        inventory={
            "plugin": "SimpleInventory",
            "options": {
                "host_file":    os.path.join(base_dir, "inventory", "hosts.yaml"),
                "group_file":   os.path.join(base_dir, "inventory", "groups.yaml"),
                "defaults_file":os.path.join(base_dir, "inventory", "defaults.yaml"),
            }
        },
        logging={"enabled": False}
    )

    for host in nr.inventory.hosts.values():
        _inject_credentials(host)

    return nr

def get_nornir_managed() -> Nornir:
    """Return Nornir instance excluding devices marked exclude_from_automation."""
    nr = get_nornir()
    return nr.filter(filter_func=lambda h: not h.data.get("exclude_from_automation", False))
