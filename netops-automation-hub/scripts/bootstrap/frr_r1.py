import time
from common import (
    connect, run, run_config,
    section, ok, warn, fail,
    FRR_USER, FRR_PASS, FRR_R1_HOST
)

console = __import__("common").console


def bootstrap(results):
    section("FRR-R1  (Edge router — AS65001)")

    conn = connect(FRR_R1_HOST, FRR_USER, FRR_PASS)
    if not conn:
        results["FRR-R1"] = {"status": "FAIL", "notes": "SSH unreachable"}
        return

    
    # ── 1. Interfaces ─────────────────────────────────────────────────────────
    console.print("  Checking interfaces...")

    ifaces = {
        "eth0": ("192.168.66.101", "192.168.66.101/24"),
        "eth1": ("10.0.12.1",      "10.0.12.1/30"),
        "eth2": ("10.0.13.1",      "10.0.13.1/30"),
    }
    for iface, (expected, cidr) in ifaces.items():
        out = run(conn, f"ip addr show {iface}")
        if expected not in out:
            warn(f"{iface} missing IP — applying...")
            run_config(conn, f"ip link set {iface} up")
            run_config(conn, f"ip addr add {cidr} dev {iface}")
            ok(f"{iface} IP assigned: {cidr}")
        else:
            ok(f"{iface} IP present: {cidr}")

    # ── 2. IPv4 forwarding ────────────────────────────────────────────────────
    console.print("  Checking IP forwarding...")
    fwd = run(conn, "cat /proc/sys/net/ipv4/ip_forward")
    if fwd.strip() != "1":
        warn("IP forwarding disabled — enabling...")
        run_config(conn, "sysctl -w net.ipv4.ip_forward=1")
        ok("IP forwarding enabled")
    else:
        ok("IP forwarding active")

    # ── 3. DNS ────────────────────────────────────────────────────────────────
    console.print("  Checking DNS...")
    dns_out = run(conn, "cat /etc/resolv.conf")
    if "8.8.8.8" not in dns_out:
        warn("DNS missing — applying...")
        run_config(conn, "sh -c 'echo nameserver 8.8.8.8 > /etc/resolv.conf'")
        ok("DNS set to 8.8.8.8")
    else:
        ok("DNS present: 8.8.8.8")

    # ── 4. Static routes ──────────────────────────────────────────────────────
    console.print("  Checking static routes...")
    route_table = run(conn, "ip route show")
    routes_needed = {
        "10.0.14.0/24": "10.0.13.2",
        "10.10.0.0/24": "10.0.13.2",
        "10.20.0.0/24": "10.0.13.2",
    }
    for subnet, gw in routes_needed.items():
        if subnet not in route_table:
            warn(f"Route {subnet} missing — adding...")
            run_config(conn, f"ip route add {subnet} via {gw}")
            ok(f"Route added: {subnet} via {gw}")
        else:
            ok(f"Route present: {subnet} via {gw}")

    # ── 5. FRR service ────────────────────────────────────────────────────────
    console.print("  Checking FRR service...")
    frr_status = run(conn, "rc-status | grep frr")
    if "started" not in frr_status:
        warn("FRR not running — restarting...")
        run_config(conn, "rc-service frr restart")
        time.sleep(5)
        ok("FRR restarted")
    else:
        ok("FRR service running")

    # ── 6. BGP session ────────────────────────────────────────────────────────
    console.print("  Waiting for BGP session with FRR-R2...")
    bgp_established = False
    for attempt in range(6):
        bgp_out = run(conn, "vtysh -c 'show bgp summary'")
        if "FRR-R2-ISP" in bgp_out and "Active" not in bgp_out and "Idle" not in bgp_out: 
            bgp_established = True
            break
        warn(f"BGP not established — attempt {attempt + 1}/6, waiting 10s...")
        time.sleep(10)

    if not bgp_established:
        fail("BGP session NOT established after 60s")
        results["FRR-R1"] = {"status": "FAIL", "notes": "BGP not established"}
        conn.disconnect()
        return

    ok("BGP session Established with FRR-R2")

    # ── 7. Default route via BGP ──────────────────────────────────────────────
    console.print("  Checking default route via BGP...")
    ip_route = run(conn, "vtysh -c 'show ip route 0.0.0.0/0'")
    if "0.0.0.0/0" not in ip_route:
        fail("Default route NOT in routing table")
        results["FRR-R1"] = {"status": "FAIL", "notes": "No default route from BGP"}
        conn.disconnect()
        return

    ok("Default route received via BGP from FRR-R2")

    # ── 8. Internet reachability ──────────────────────────────────────────────
    console.print("  Testing internet reachability...")
    ping_out = run(conn, "ping -c3 8.8.8.8")
    if "packets received" in ping_out:
        ok("Internet reachable from FRR-R1")
        results["FRR-R1"] = {"status": "PASS", "notes": "All checks passed"}
    else:
        fail("Internet NOT reachable from FRR-R1")
        results["FRR-R1"] = {"status": "FAIL", "notes": "Internet ping failed"}


    conn.disconnect()
