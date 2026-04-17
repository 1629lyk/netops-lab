"""
devices.py — GET /devices
Returns all devices from Nornir inventory with reachability status.
"""

from fastapi import APIRouter
from src.core.engine import get_nornir
from nornir_netmiko.tasks import netmiko_send_command

router = APIRouter(prefix="/devices", tags=["devices"])


def _ping_task(task):
    """Simple connectivity check per device."""
    try:
        result = task.run(
            task=netmiko_send_command,
            command_string="uname -n" if task.host.platform == "linux" else "show version | include Version",
            use_timing=True
        )
        return {"reachable": True, "output": result[0].result.strip().splitlines()[0][:60]}
    except Exception as e:
        return {"reachable": False, "output": str(e)}


@router.get("")
def list_devices():
    """List all devices with live reachability status."""
    nr = get_nornir()
    results = nr.run(task=_ping_task)

    devices = []
    for host, result in results.items():
        host_obj = nr.inventory.hosts[host]
        if result.failed:
            reachable = False
            output = str(result.exception)
        else:
            data = result[0].result
            reachable = data["reachable"]
            output = data["output"]

        devices.append({
            "hostname": host,
            "ip": str(host_obj.hostname),
            "platform": host_obj.platform,
            "role": host_obj.data.get("role", "unknown"),
            "site": host_obj.data.get("site", "unknown"),
            "reachable": reachable,
            "output": output
        })

    return {"devices": devices, "total": len(devices)}
