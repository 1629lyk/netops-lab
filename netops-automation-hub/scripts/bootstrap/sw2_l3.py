from common import (
    connect, run, run_config,
    section, ok, warn, fail,
    CISCO_USER, CISCO_PASS, CISCO_EN, SW2_HOST
)

console = __import__("common").console


def bootstrap(results):
    section("SW2-L3  (Distribution switch)")

    conn = connect(
        SW2_HOST, CISCO_USER, CISCO_PASS,
        device_type="cisco_ios",
        secret=CISCO_EN
    )
    if not conn:
        results["SW2-L3"] = {"status": "FAIL", "notes": "SSH unreachable"}
        return

    # ── 1. IP routing ─────────────────────────────────────────────────────────
    console.print("  Checking IP routing...")
    run_out = run(conn, "show run | include ip routing")
    if "ip routing" not in run_out:
        warn("IP routing disabled — enabling...")
        conn.send_config_set(["ip routing"])
        ok("IP routing enabled")
    else:
        ok("IP routing active")

    # ── 2. SVI state ──────────────────────────────────────────────────────────
    console.print("  Checking SVIs...")
    int_out = run(conn, "show ip interface brief")

    svis = {
        "Vlan10": "10.10.0.1",
        "Vlan20": "10.20.0.1",
    }
    for svi, expected_ip in svis.items():
        if expected_ip not in int_out:
            fail(f"{svi} missing IP {expected_ip} — check SW2 config manually")
            results["SW2-L3"] = {"status": "FAIL", "notes": f"{svi} IP missing"}
            conn.disconnect()
            return
        else:
            ok(f"{svi} IP present: {expected_ip}")

    # ── 3. Uplink interface ───────────────────────────────────────────────────
    console.print("  Checking uplink to ASA...")
    if "10.0.14.2" not in int_out:
        fail("Ethernet0/0 missing IP 10.0.14.2 — check SW2 config manually")
        results["SW2-L3"] = {"status": "FAIL", "notes": "Uplink IP missing"}
        conn.disconnect()
        return
    else:
        ok("Ethernet0/0 IP present: 10.0.14.2")

    # ── 4. Default route ──────────────────────────────────────────────────────
    console.print("  Checking default route...")
    route_out = run(conn, "show ip route")
    if "10.0.14.1" not in route_out:
        warn("Default route missing — adding...")
        conn.send_config_set(["ip route 0.0.0.0 0.0.0.0 10.0.14.1"])
        ok("Default route added via 10.0.14.1")
    else:
        ok("Default route present via 10.0.14.1")

    # ── 5. Trunk to SW1 ───────────────────────────────────────────────────────
    console.print("  Checking trunk to SW1-L2...")
    trunk_out = run(conn, "show interfaces trunk")
    if "Et0/1" in trunk_out or "Ethernet0/1" in trunk_out:
        ok("Trunk to SW1-L2 active on Ethernet0/1")
    else:
        warn("Trunk may be down on Ethernet0/1 — verify manually")

    # ── 6. Internet reachability ──────────────────────────────────────────────
    console.print("  Testing internet reachability...")
    ping_out = run(conn, "ping 8.8.8.8")
    if "!!" in ping_out or "Success rate is 100" in ping_out:
        ok("Internet reachable from SW2-L3")
        results["SW2-L3"] = {"status": "PASS", "notes": "All checks passed"}
    elif "Success rate is" in ping_out and "0 percent" not in ping_out:
        ok("Internet partially reachable from SW2-L3")
        results["SW2-L3"] = {"status": "PASS", "notes": "Partial internet — acceptable"}
    else:
        fail("Internet NOT reachable from SW2-L3")
        results["SW2-L3"] = {"status": "FAIL", "notes": "Internet ping failed"}



    conn.disconnect()
