"""
facts.py — Nornir device facts collection
Pulls hostname, platform, and version from each device.
"""

from nornir_netmiko.tasks import netmiko_send_command

# Command to pull version info per platform
FACTS_COMMANDS = {
    "linux":      "vtysh -c 'show version'",
    "cisco_ios":  "show version | include Version|uptime",
    "cisco_asa":  "show version | include Version|uptime",
}


def get_facts(task):
    """Collect basic facts from a device."""
    platform = task.host.platform
    hostname = task.host.name
    cmd = FACTS_COMMANDS.get(platform, "show version")

    result = task.run(
        task=netmiko_send_command,
        command_string=cmd,
        use_timing=True
    )

    output = result[0].result.strip()
    first_line = output.splitlines()[0] if output else "no output"

    return {
        "hostname": hostname,
        "platform": platform,
        "version_line": first_line,
        "raw": output
    }
