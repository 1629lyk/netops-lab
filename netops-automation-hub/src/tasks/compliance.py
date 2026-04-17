"""
compliance.py — Nornir compliance engine
Runs policy checks per device type, stores results in PostgreSQL.
"""

from datetime import datetime
from nornir_netmiko.tasks import netmiko_send_command
from src.database.session import get_session
from src.database.models import ComplianceResult


# ── Policy definitions ────────────────────────────────────────────────────────

def _check_ssh_enabled(output, hostname):
    """All devices — SSH service must be listening."""
    passed = "ssh" in output.lower() or "enabled" in output.lower()
    return {
        "policy": "ssh_enabled",
        "passed": passed,
        "detail": "SSH found in process list" if passed else "SSH not found in process list"
    }



def _check_bgp_state(output, hostname):
    """FRR only — BGP neighbors must not be Active or Idle."""
    passed = "Active" not in output and "Idle" not in output and len(output.strip()) > 0
    return {
        "policy": "bgp_neighbor_state",
        "passed": passed,
        "detail": "BGP neighbors up" if passed else "BGP neighbor in Active/Idle state"
    }


def _check_password_encryption(output, hostname):
    """Cisco IOS only — service password-encryption must be enabled."""
    passed = "service password-encryption" in output
    return {
        "policy": "password_encryption",
        "passed": passed,
        "detail": "service password-encryption present" if passed else "service password-encryption missing"
    }


def _check_no_permit_any(output, hostname):
    """ASA only — no unrestricted permit any any in ACLs."""
    lines = output.lower().splitlines()
    violations = [l for l in lines if "permit" in l and l.count("any") >= 2]
    passed = len(violations) == 0
    return {
        "policy": "no_permit_any_any",
        "passed": passed,
        "detail": "No permit any any found" if passed else f"{len(violations)} permit any any rule(s) found"
    }


# ── Commands per policy per platform ─────────────────────────────────────────

POLICY_MAP = {
    "linux": [
        ("ps aux",                          _check_ssh_enabled),
        ("vtysh -c 'show bgp summary'",     _check_bgp_state),
    ],
    "cisco_ios": [
        ("show ip ssh",      _check_ssh_enabled),
        ("show run | include password-encryption", _check_password_encryption),
    ],
    "cisco_asa": [
        ("show process | include ssh",      _check_ssh_enabled),
        ("show access-list",                _check_no_permit_any),
    ],
}


# ── Main task ─────────────────────────────────────────────────────────────────

def check_compliance(task):
    """Run all applicable policy checks for a device and store results in DB."""
    platform = task.host.platform
    hostname = task.host.name
    policies = POLICY_MAP.get(platform, [])
    results = []

    for cmd, check_fn in policies:
        try:
            result = task.run(
                task=netmiko_send_command,
                command_string=cmd,
                use_timing=True
            )
            output = result[0].result
        except Exception as e:
            output = ""

        check_result = check_fn(output, hostname)
        results.append(check_result)

    # Store all results in DB
    session = get_session()
    try:
        for r in results:
            record = ComplianceResult(
                hostname=hostname,
                policy=r["policy"],
                passed=r["passed"],
                detail=r["detail"],
                checked_at=datetime.now()
            )
            session.add(record)
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

    return results
