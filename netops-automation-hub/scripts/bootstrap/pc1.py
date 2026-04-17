from common import (
    connect, run, run_config,
    section, ok, warn, fail,
    PC_USER, PC1_PASS, PC1_HOST
)

console = __import__("common").console


def bootstrap(results):
    section("PC1  (VLAN10 — 10.10.0.11)")

    conn = connect(PC1_HOST, PC_USER, PC1_PASS)
    if not conn:
        results["PC1"] = {"status": "FAIL", "notes": "SSH unreachable"}
        return

    # ── 1. Interface ──────────────────────────────────────────────────────────
    console.print("  Checking eth0...")
    eth0_out = run(conn, "ip addr show eth0")
    if "10.10.0.11" not in eth0_out:
        warn("eth0 missing IP — applying...")
        run_config(conn, "ip link set eth0 mtu 1500")
        run_config(conn, "ip link set eth0 up")
        run_config(conn, "ip addr add 10.10.0.11/24 dev eth0")
        ok("eth0 IP assigned: 10.10.0.11/24")
    else:
        ok("eth0 IP present: 10.10.0.11/24")

    # ── 2. Default route ──────────────────────────────────────────────────────
    console.print("  Checking default route...")
    route_out = run(conn, "ip route show default")
    if "10.10.0.1" not in route_out:
        warn("Default route missing — applying...")
        run_config(conn, "ip route add default via 10.10.0.1")
        ok("Default route added via 10.10.0.1")
    else:
        ok("Default route present via 10.10.0.1")

    # ── 3. DNS ────────────────────────────────────────────────────────────────
    console.print("  Checking DNS...")
    dns_out = run(conn, "cat /etc/resolv.conf")
    if "8.8.8.8" not in dns_out:
        warn("DNS missing — applying...")
        run_config(conn, "sh -c 'echo nameserver 8.8.8.8 > /etc/resolv.conf'")
        ok("DNS set to 8.8.8.8")
    else:
        ok("DNS present: 8.8.8.8")

    # ── 4. SSH service ────────────────────────────────────────────────────────
    console.print("  Checking SSH service...")
    ssh_out = run(conn, "service ssh status")
    if "running" not in ssh_out:
        warn("SSH not running — starting...")
        run_config(conn, "service ssh start")
        ok("SSH started")
    else:
        ok("SSH service running")

    # ── 5. Internet reachability ──────────────────────────────────────────────
    console.print("  Testing internet reachability...")
    ping_out = run(conn, "ping -c 4 8.8.8.8")
    if " received" in ping_out and "0 received" not in ping_out:
        ok("Internet reachable from PC1")
        results["PC1"] = {"status": "PASS", "notes": "All checks passed"}
    else:
        fail("Internet NOT reachable from PC1")
        results["PC1"] = {"status": "FAIL", "notes": "Internet ping failed"}

    conn.disconnect()
