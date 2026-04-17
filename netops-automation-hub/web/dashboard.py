"""
dashboard.py — NetOps Automation Hub NOC Dashboard
Streamlit dashboard consuming FastAPI endpoints.
"""

import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time

# ── Config ────────────────────────────────────────────────────────────────────
API_BASE = "http://127.0.0.1:8000"
REFRESH_INTERVAL = 300  # 5 minutes in seconds

st.set_page_config(
    page_title="NetOps Automation Hub",
    page_icon="🌐",
    layout="wide"
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def fetch(endpoint, timeout=30):
    """Fetch data from FastAPI endpoint."""
    try:
        r = requests.get(f"{API_BASE}{endpoint}", timeout=timeout)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)

@st.cache_data(ttl=60)
def fetch_devices():
    return fetch("/devices", timeout=60)


def last_backup_per_device(backups):
    """Return only the most recent backup per device."""
    seen = {}
    for b in backups:
        if b["hostname"] not in seen:
            seen[b["hostname"]] = b
    return list(seen.values())


def latest_compliance_per_device_policy(results):
    """Return only the most recent result per device+policy combination."""
    seen = {}
    for r in results:
        key = (r["hostname"], r["policy"])
        if key not in seen:
            seen[key] = r
    return list(seen.values())


# ── Header ────────────────────────────────────────────────────────────────────

st.title("🌐 NetOps Automation Hub")
st.caption("NOC Dashboard — Network Automation & Compliance Monitor")

col_time, col_btn = st.columns([4, 1])
with col_time:
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
with col_btn:
    manual_refresh = st.button("🔄 Refresh Now")

st.divider()

# ── Health Bar ────────────────────────────────────────────────────────────────

st.subheader("🏥 System Health")
health_data, health_err = fetch("/health")

if health_err:
    st.error(f"Health check failed: {health_err}")
else:
    services = health_data.get("services", {})
    h1, h2, h3, h4 = st.columns(4)

    overall = health_data.get("status", "unknown")
    h1.metric("Overall", "✅ OK" if overall == "ok" else "⚠️ Degraded")
    h2.metric("API",      "✅ OK" if services.get("api") == "ok" else "❌ Error")
    h3.metric("Database", "✅ OK" if services.get("database") == "ok" else "❌ Error")
    h4.metric("Redis",    "✅ OK" if services.get("redis") == "ok" else "❌ Error")

st.divider()

# ── Device Status ─────────────────────────────────────────────────────────────

st.subheader("📡 Device Status")
devices_data, devices_err = fetch_devices()

if devices_err:
    st.error(f"Could not fetch devices: {devices_err}")
else:
    devices = devices_data.get("devices", [])
    if devices:
        rows = []
        for d in devices:
            rows.append({
                "Hostname":  d["hostname"],
                "IP":        d["ip"],
                "Platform":  d["platform"],
                "Role":      d["role"],
                "Site":      d["site"],
                "Reachable": "✅ Yes" if d["reachable"] else "❌ No",
                "Output":    d["output"]
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
        total = len(devices)
        reachable = sum(1 for d in devices if d["reachable"])
        st.caption(f"{reachable}/{total} devices reachable")
    else:
        st.warning("No devices found.")

st.divider()

# ── Last Backup Per Device ────────────────────────────────────────────────────

st.subheader("💾 Last Config Backup")
configs_data, configs_err = fetch("/configs")

if configs_err:
    st.error(f"Could not fetch backups: {configs_err}")
else:
    backups = configs_data.get("backups", [])
    if backups:
        latest = last_backup_per_device(backups)
        rows = []
        for b in latest:
            backed_at = datetime.fromisoformat(b["backed_up_at"])
            age_mins = int((datetime.utcnow() - backed_at).total_seconds() / 60)
            rows.append({
                "Hostname":    b["hostname"],
                "Backed Up":   backed_at.strftime("%Y-%m-%d %H:%M:%S"),
                "Age (mins)":  age_mins,
                "Lines":       b["lines"],
                "Status":      "✅ OK" if b["success"] else "❌ Failed"
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        col_b1, col_b2 = st.columns([1, 4])
        with col_b1:
            if st.button("▶ Run Backup Now"):
                with st.spinner("Running backup against all devices..."):
                    try:
                        r = requests.post(f"{API_BASE}/configs/backup", timeout=120)
                        st.success("Backup complete — refresh to see latest results.")
                    except Exception as e:
                        st.error(f"Backup failed: {e}")
    else:
        st.warning("No backups found. Run a backup first.")

st.divider()

# ── Compliance Summary ────────────────────────────────────────────────────────

st.subheader("🛡️ Compliance Summary")
compliance_data, compliance_err = fetch("/compliance")

if compliance_err:
    st.error(f"Could not fetch compliance results: {compliance_err}")
else:
    results = compliance_data.get("results", [])
    if results:
        latest = latest_compliance_per_device_policy(results)
        rows = []
        for r in latest:
            checked_at = datetime.fromisoformat(r["checked_at"])
            rows.append({
                "Hostname": r["hostname"],
                "Policy":   r["policy"],
                "Status":   "✅ PASS" if r["passed"] else "❌ FAIL",
                "Detail":   r["detail"],
                "Checked":  checked_at.strftime("%Y-%m-%d %H:%M:%S")
            })
        df = pd.DataFrame(rows)

        # Summary metrics
        total_checks = len(rows)
        passed = sum(1 for r in latest if r["passed"])
        failed = total_checks - passed
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Checks", total_checks)
        c2.metric("Passed", passed, delta=None)
        c3.metric("Failed", failed, delta=None)

        st.dataframe(df, use_container_width=True, hide_index=True)

        col_c1, col_c2 = st.columns([1, 4])
        with col_c1:
            if st.button("▶ Run Compliance Now"):
                with st.spinner("Running compliance checks..."):
                    try:
                        r = requests.post(f"{API_BASE}/compliance/run", timeout=120)
                        st.success("Compliance check complete — refresh to see latest results.")
                    except Exception as e:
                        st.error(f"Compliance check failed: {e}")
    else:
        st.warning("No compliance results found. Run a compliance check first.")

# ── Auto Refresh ──────────────────────────────────────────────────────────────

st.divider()
st.caption(f"⏱ Auto-refresh every {REFRESH_INTERVAL // 60} minutes.")
time.sleep(REFRESH_INTERVAL)
st.rerun()
