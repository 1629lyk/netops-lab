# Web — Streamlit NOC Dashboard

Real-time NOC dashboard built with Streamlit. Consumes the FastAPI REST API for all data.

---

## Running the Dashboard

```bash
source venv/bin/activate
streamlit run web/dashboard.py --server.port 8501 --server.address 0.0.0.0
```

Access from Windows host: `http://192.168.66.131:8501`

> The FastAPI server must be running on port 8000 before starting the dashboard.

---

## Dashboard Panels

### System Health
Displays live status of API, PostgreSQL, and Redis by calling `GET /health`.

| Indicator | Source |
|---|---|
| Overall status | /health → status field |
| API | /health → services.api |
| Database | /health → services.database |
| Redis | /health → services.redis |

### Device Status
Shows all 5 lab devices with live reachability. Calls `GET /devices`.

| Column | Description |
|---|---|
| Hostname | Device name from Nornir inventory |
| IP | Management IP |
| Platform | linux, cisco_ios, cisco_asa |
| Role | router, firewall, l3switch, l2switch |
| Site | core, isp, edge, distribution, access |
| Reachable | Live SSH check result |

> Device status is cached for 60 seconds to avoid repeated SSH connections on every page load.

### Last Config Backup
Shows the most recent backup per device from `GET /configs`. Displays age in minutes.

Includes **Run Backup Now** button that calls `POST /configs/backup`.

### Compliance Summary
Shows latest compliance result per device per policy from `GET /compliance`.

Displays summary metrics — total checks, passed, failed.

Includes **Run Compliance Now** button that calls `POST /compliance/run`.

---

## Refresh Behavior

| Type | Behavior |
|---|---|
| Auto refresh | Page reruns every 5 minutes automatically |
| Manual refresh | Click **Refresh Now** button at top of page |
| Run backup | Triggers live backup, refresh to see new results |
| Run compliance | Triggers live compliance check, refresh to see new results |

---

## API Endpoints Consumed

| Endpoint | Panel |
|---|---|
| GET /health | System Health |
| GET /devices | Device Status |
| GET /configs | Last Config Backup |
| POST /configs/backup | Run Backup Now button |
| GET /compliance | Compliance Summary |
| POST /compliance/run | Run Compliance Now button |

---

## Timezone

Timestamps are stored in UTC in PostgreSQL and converted to America/Los_Angeles for display using Python's `zoneinfo` module.

---

## Known Behavior

- Compliance and backup panels show last recorded results — they do not run live checks on page load
- Device status panel does run live SSH checks — first load may take 20-30 seconds
- After clicking Run Backup or Run Compliance, click Refresh Now to see updated results
