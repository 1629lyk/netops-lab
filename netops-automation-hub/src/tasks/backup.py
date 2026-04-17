"""
backup.py — Nornir config backup task
Pulls running config from each device, saves to configs/ and inserts metadata to PostgreSQL.
"""

import os
from datetime import datetime
from nornir_netmiko.tasks import netmiko_send_command
from src.database.session import get_session, init_db
from src.database.models import ConfigBackup

# Project root configs/ directory
CONFIGS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'configs')

# Command to pull running config per platform
BACKUP_COMMANDS = {
    "linux":      "vtysh -c 'show running-config'",
    "cisco_ios":  "show running-config",
    "cisco_asa":  "show running-config",
}


def backup_config(task):
    """Pull running config and save to file + DB."""
    platform = task.host.platform
    hostname = task.host.name
    cmd = BACKUP_COMMANDS.get(platform, "show running-config")

    # Pull config
    result = task.run(
        task=netmiko_send_command,
        command_string=cmd,
        use_timing=True
    )

    config_output = result[0].result
    success = bool(config_output and len(config_output.strip()) > 0)

    # Build file path
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    host_dir = os.path.join(CONFIGS_DIR, hostname)
    os.makedirs(host_dir, exist_ok=True)
    filepath = os.path.join(host_dir, f"{hostname}_{timestamp}.txt")

    # Save to file
    if success:
        with open(filepath, "w") as f:
            f.write(config_output)
        lines = len(config_output.splitlines())
    else:
        lines = 0

    # Insert metadata to DB
    session = get_session()
    try:
        record = ConfigBackup(
            hostname=hostname,
            filepath=filepath,
            backed_up_at=datetime.now(),
            success=success,
            lines=lines
        )
        session.add(record)
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

    return {
        "hostname": hostname,
        "filepath": filepath,
        "success": success,
        "lines": lines
    }
