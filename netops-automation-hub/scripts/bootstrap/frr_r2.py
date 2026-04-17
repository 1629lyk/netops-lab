import time
from common import (
    connect, run, run_config,
    section, ok, warn, fail,
    FRR_USER, FRR_PASS, FRR_R2_HOST
)

console = __import__("common").console

def bootstrap(results):
    section("FRR-R2  (ISP router — AS65002)")

    conn = connect(FRR_R2_HOST, FRR_USER, FRR_PASS)
    if not conn:
        results["FRR-R2"] = {"status": "FAIL", "notes": "SSH unreachable"}
        return

    # ── 1. Interfaces ─────────────────────────────────────────────────────────
    console_check = {
        "eth0": ("192.168.254.135", "192.168.254.135/24"),
        "eth1": ("10.0.12.2",       "10.0.12.2/30"),
    }
   # console_print = __import__("common").console

    console.print("  Checking interfaces...")
    for iface, (expected_ip, cidr) in console_check.items():
        out = run(conn, f"ip addr show {iface}")
        if expected_ip not in out:
            warn(f"{iface} missing IP — applying...")
            run_config(conn, f"ip link set {iface} up")
            run_config(conn, f"ip addr add {cidr} dev {iface}")
            ok(f"{iface} IP assigned: {cidr}")
        else:
            ok(f"{iface} IP present: {cidr}")

    # ── 2. Default route ──────────────────────────────────────────────────────
    console.print("  Checking default route...")
    route_out = run(conn, "ip route show")
    if "default via 192.168.254.2" not in route_out:
        warn("Default route missing — applying...")
        run_config(conn, "ip route add default via 192.168.254.2 dev eth0")
        ok("Default route added via 192.168.254.2")
    else:
        ok("Default route present via 192.168.254.2")

    # ── 3. DNS ────────────────────────────────────────────────────────────────
    console.print("  Checking DNS...")
    dns_out = run(conn, "cat /etc/resolv.conf")
    if "8.8.8.8" not in dns_out:
        warn("DNS missing — applying...")
        run_config(conn, "sh -c 'echo nameserver 8.8.8.8 > /etc/resolv.conf'")
        ok("DNS set to 8.8.8.8")
    else:
        ok("DNS present: 8.8.8.8")

    # ── 4. IPv4 forwarding ────────────────────────────────────────────────────
    console.print("  Checking IP forwarding...")
    fwd = run(conn, "cat /proc/sys/net/ipv4/ip_forward")
    if fwd.strip() != "1":
        warn("IP forwarding disabled — enabling...")
        run_config(conn, "sysctl -w net.ipv4.ip_forward=1")
        ok("IP forwarding enabled")
    else:
        ok("IP forwarding active")

    # ── 5. NAT masquerade ─────────────────────────────────────────────────────
    console.print("  Checking NAT masquerade...")
    nat_out = run(conn, "iptables -t nat -L POSTROUTING -n")
    if "MASQUERADE" not in nat_out:
        warn("NAT masquerade missing — applying...")
        run_config(conn, "iptables -F FORWARD")
        run_config(conn, "iptables -t nat -F POSTROUTING")
        run_config(conn, "iptables -t nat -A POSTROUTING -s 10.0.0.0/8 -o eth0 -j MASQUERADE")
        run_config(conn, "iptables -A FORWARD -i eth1 -o eth0 -j ACCEPT")
        run_config(conn, "iptables -A FORWARD -i eth0 -o eth1 -m state --state RELATED,ESTABLISHED -j ACCEPT")
        ok("NAT masquerade applied")
    else:
        ok("NAT masquerade active")

    # ── 6. Return routes ──────────────────────────────────────────────────────
    console.print("  Checking return routes...")
    route_table = run(conn, "ip route show")
    routes_needed = {
        "10.0.13.0/30": "10.0.12.1",
        "10.0.14.0/24": "10.0.12.1",
        "10.10.0.0/24": "10.0.12.1",
        "10.20.0.0/24": "10.0.12.1",
    }
    for subnet, gw in routes_needed.items():
        if subnet not in route_table:
            warn(f"Route {subnet} missing — adding...")
            run_config(conn, f"ip route add {subnet} via {gw}")
            ok(f"Route added: {subnet} via {gw}")
        else:
            ok(f"Route present: {subnet} via {gw}")

    # ── 7. FRR service ────────────────────────────────────────────────────────
    console.print("  Checking FRR service...")
    frr_status = run(conn, "rc-status | grep frr")
    if "started" not in frr_status:
        warn("FRR not running — starting...")
        run_config(conn, "rc-service frr restart")
        time.sleep(5)
        ok("FRR restarted")
    else:
        ok("FRR service running")

    # ── 8. Internet reachability ──────────────────────────────────────────────
    console.print("  Testing internet reachability...")
    ping_out = run(conn, "ping -c 4 8.8.8.8")
    if "packets received" in ping_out:
        ok("Internet reachable from FRR-R2")
        results["FRR-R2"] = {"status": "PASS", "notes": "All checks passed"}
    else:
        fail("Internet NOT reachable from FRR-R2")
        results["FRR-R2"] = {"status": "FAIL", "notes": "Internet ping failed"}


    # ── 9. Management loopback + return route ─────────────────────────────────
    console.print("  Checking management loopback and return route...")
    lo_out = run(conn, "ip addr show lo")
    if "10.0.99.2" not in lo_out:
        warn("Loopback 10.0.99.2 missing — applying...")
        run_config(conn, "ip addr add 10.0.99.2/32 dev lo")
        ok("Loopback 10.0.99.2 added")
    else:
        ok("Loopback 10.0.99.2 present")

    route_table2 = run(conn, "ip route show")
    if "192.168.66.0/24" not in route_table2:
        warn("Return route to mgmt subnet missing — applying...")
        run_config(conn, "ip route add 192.168.66.0/24 via 10.0.12.1")
        ok("Return route added: 192.168.66.0/24 via 10.0.12.1")
    else:
        ok("Return route present: 192.168.66.0/24 via 10.0.12.1")



    conn.disconnect()
