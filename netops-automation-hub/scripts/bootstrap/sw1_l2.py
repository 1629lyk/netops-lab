from common import (
    connect, run, run_config,
    section, ok, warn, fail,
    CISCO_USER, CISCO_PASS, CISCO_EN, SW1_HOST
)

console = __import__("common").console


def bootstrap(results):
    section("SW1-L2  (Access switch)")

    conn = connect(
        SW1_HOST, CISCO_USER, CISCO_PASS,
        device_type="cisco_ios",
        secret=CISCO_EN
    )
    if not conn:
        results["SW1-L2"] = {"status": "FAIL", "notes": "SSH unreachable"}
        return

    # ── 1. SVI state ──────────────────────────────────────────────────────────
    console.print("  Checking management SVI...")
    int_out = run(conn, "show ip interface brief")

    if "10.10.0.254" not in int_out:
        fail("Vlan10 SVI missing IP 10.10.0.254 — check SW1 config manually")
        results["SW1-L2"] = {"status": "FAIL", "notes": "Vlan10 SVI IP missing"}
        conn.disconnect()
        return
    else:
        ok("Vlan10 SVI IP present: 10.10.0.254")

    # ── 2. Default gateway ────────────────────────────────────────────────────
    console.print("  Checking default gateway...")
    gw_out = run(conn, "show run | include default-gateway")
    if "10.10.0.1" not in gw_out:
        warn("Default gateway missing — applying...")
        conn.send_config_set(["ip default-gateway 10.10.0.1"])
        ok("Default gateway set to 10.10.0.1")
    else:
        ok("Default gateway present: 10.10.0.1")

    # ── 3. Trunk to SW2 ───────────────────────────────────────────────────────
    console.print("  Checking trunk to SW2-L3...")
    trunk_out = run(conn, "show interfaces trunk")
    if "Et0/0" in trunk_out or "Ethernet0/0" in trunk_out:
        ok("Trunk to SW2-L3 active on Ethernet0/0")
    else:
        warn("Trunk may be down on Ethernet0/0 — verify manually")

    # ── 4. VLAN access ports ──────────────────────────────────────────────────
    console.print("  Checking access ports...")
    vlan_out = run(conn, "show vlan brief")
    if "10" in vlan_out:
        ok("VLAN10 present")
    else:
        warn("VLAN10 missing — verify manually")

    if "20" in vlan_out:
        ok("VLAN20 present")
    else:
        warn("VLAN20 missing — verify manually")

    # ── 5. Reachability ───────────────────────────────────────────────────────
    console.print("  Testing reachability to SW2-L3...")
    ping_out = run(conn, "ping 10.10.0.1")
    if "!!" in ping_out or "Success rate is 100" in ping_out:
        ok("SW2-L3 reachable from SW1-L2")
        results["SW1-L2"] = {"status": "PASS", "notes": "All checks passed"}
    elif "Success rate is" in ping_out and "0 percent" not in ping_out:
        ok("SW2-L3 partially reachable")
        results["SW1-L2"] = {"status": "PASS", "notes": "Partial reachability — acceptable"}
    else:
        fail("SW2-L3 NOT reachable from SW1-L2")
        results["SW1-L2"] = {"status": "FAIL", "notes": "Gateway ping failed"}


    conn.disconnect()
