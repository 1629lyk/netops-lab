from common import (
    connect, run, run_config,
    section, ok, warn, fail,
    ASA_USER, ASA_PASS, ASA_EN, ASA_HOST
)

console = __import__("common").console


def bootstrap(results):
    section("ASA-FW  (Firewall)")

    conn = connect(
        ASA_HOST, ASA_USER, ASA_PASS,
        device_type="cisco_asa",
        secret=ASA_EN
    )
    if not conn:
        results["ASA-FW"] = {"status": "FAIL", "notes": "SSH unreachable"}
        return

    # ── 1. Interface state ────────────────────────────────────────────────────
    console.print("  Checking interfaces...")
    int_out = run(conn, "show interface ip brief")

    interfaces = {
        "GigabitEthernet0/0": "10.0.13.2",
        "GigabitEthernet0/1": "10.0.14.1",
    }
    for iface, expected_ip in interfaces.items():
        if expected_ip not in int_out:
            fail(f"{iface} missing IP {expected_ip} — check ASA config manually")
            results["ASA-FW"] = {"status": "FAIL", "notes": f"{iface} IP missing"}
            conn.disconnect()
            return
        else:
            ok(f"{iface} IP present: {expected_ip}")

    # ── 2. Access groups ──────────────────────────────────────────────────────
    console.print("  Checking access-groups...")
    acl_out = run(conn, "show run access-group")

    if "OUTSIDE_IN" not in acl_out:
        warn("OUTSIDE_IN access-group missing — applying...")
        run_config(conn, "access-list OUTSIDE_IN extended permit ip any any")
        run_config(conn, "access-group OUTSIDE_IN in interface outside")
        ok("OUTSIDE_IN applied")
    else:
        ok("OUTSIDE_IN access-group present")

    if "INSIDE_OUT" not in acl_out:
        warn("INSIDE_OUT access-group missing — applying...")
        run_config(conn, "access-list INSIDE_OUT extended permit ip any any")
        run_config(conn, "access-group INSIDE_OUT in interface inside")
        ok("INSIDE_OUT applied")
    else:
        ok("INSIDE_OUT access-group present")

    # ── 3. Inside routes ──────────────────────────────────────────────────────
    console.print("  Checking inside routes...")
    route_out = run(conn, "show route")

    inside_routes = {
        "10.10.0.0": "route inside 10.10.0.0 255.255.255.0 10.0.14.2",
        "10.20.0.0": "route inside 10.20.0.0 255.255.255.0 10.0.14.2",
    }
    for subnet, route_cmd in inside_routes.items():
        if subnet not in route_out:
            warn(f"Route {subnet} missing — adding...")
            run_config(conn, route_cmd)
            ok(f"Route added: {subnet}")
        else:
            ok(f"Route present: {subnet}")

    # ── 4. Default route ──────────────────────────────────────────────────────
    console.print("  Checking default route...")
    if "10.0.13.1" not in route_out:
        warn("Default route missing — adding...")
        run_config(conn, "route outside 0.0.0.0 0.0.0.0 10.0.13.1 1")
        ok("Default route added via 10.0.13.1")
    else:
        ok("Default route present via 10.0.13.1")

    # ── 5. ICMP inspection ────────────────────────────────────────────────────
    console.print("  Checking ICMP inspection...")
    policy_out = run(conn, "show run policy-map")
    if "inspect icmp" not in policy_out:
        warn("ICMP inspection missing — applying...")
        run_config(conn, "policy-map global_policy")
        run_config(conn, " class inspection_default")
        run_config(conn, "  inspect icmp")
        run_config(conn, "service-policy global_policy global")
        ok("ICMP inspection applied")
    else:
        ok("ICMP inspection active")

    # ── 6. Internet reachability ──────────────────────────────────────────────
    console.print("  Testing internet reachability...")
    ping_out = run(conn, "ping 8.8.8.8")
    if "!!" in ping_out or "Success rate is 100" in ping_out:
        ok("Internet reachable from ASA-FW")
        results["ASA-FW"] = {"status": "PASS", "notes": "All checks passed"}
    elif "Success rate is" in ping_out and "0 percent" not in ping_out:
        ok("Internet partially reachable from ASA-FW")
        results["ASA-FW"] = {"status": "PASS", "notes": "Partial internet — acceptable"}
    else:
        fail("Internet NOT reachable from ASA-FW")
        results["ASA-FW"] = {"status": "FAIL", "notes": "Internet ping failed"}


    conn.disconnect()
