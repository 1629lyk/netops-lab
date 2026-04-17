# src

Core application code for the NetOps Automation Hub.

---

## Directory Structure

```
src/
├── api/
│   ├── main.py            # FastAPI app entry point
│   ├── dependencies.py    # Shared DB session dependency
│   └── routers/
│       ├── health.py      # GET /health
│       ├── devices.py     # GET /devices
│       ├── configs.py     # GET /configs, POST /configs/backup
│       └── compliance.py  # GET /compliance, POST /compliance/run
├── core/
│   └── engine.py          # Nornir initialization + credential injection
├── database/
│   ├── models.py          # SQLAlchemy table definitions
│   └── session.py         # DB engine + session factory
├── tasks/
│   ├── backup.py          # Config backup Nornir task
│   ├── compliance.py      # Compliance check Nornir task
│   └── facts.py           # Device facts collection task
├── parsers/               # TextFSM/Genie parsers (future)
└── utils/                 # Shared utilities (future)
```

---

## API — src/api/

### Running the API

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Swagger UI available at: `http://192.168.66.131:8000/docs`

### Endpoints

#### GET /health
Returns status of API, PostgreSQL, and Redis.

```json
{
  "status": "ok",
  "services": {
    "api": "ok",
    "database": "ok",
    "redis": "ok"
  }
}
```

#### GET /devices
Returns all 5 inventory devices with live SSH reachability check.

```json
{
  "devices": [
    {
      "hostname": "frr-r1",
      "ip": "192.168.66.101",
      "platform": "linux",
      "role": "router",
      "site": "core",
      "reachable": true,
      "output": "frr"
    }
  ],
  "total": 5
}
```

> Note: ASA is shown in device list but excluded from automated tasks.

#### GET /configs
Returns all config backup records from PostgreSQL, most recent first.

#### POST /configs/backup
Triggers synchronous config backup against all managed devices. Returns per-device results.

#### GET /compliance
Returns all compliance check results from PostgreSQL, most recent first.

#### POST /compliance/run
Triggers synchronous compliance check against all managed devices. Returns per-device policy results.

---

## Nornir Engine — src/core/engine.py

### Functions

#### get_nornir()
Initializes Nornir with full inventory including ASA. Used by `/devices` endpoint to show all devices.

#### get_nornir_managed()
Returns Nornir filtered to exclude devices with `exclude_from_automation: true` in hosts.yaml. Used by all backup and compliance tasks.

### Credential Injection

Credentials are never stored in YAML files. `_inject_credentials()` reads from `.env` at runtime and injects into each host object based on group membership:

| Group | Credentials Used |
|---|---|
| frr | FRR_USERNAME, FRR_PASSWORD |
| cisco_ios | CISCO_USERNAME, CISCO_PASSWORD, CISCO_ENABLE |
| cisco_asa | ASA_USERNAME, ASA_PASSWORD, ASA_ENABLE |

---

## Database — src/database/

### models.py

#### config_backups table

| Column | Type | Description |
|---|---|---|
| id | integer PK | Auto-increment |
| hostname | varchar(64) | Device name |
| filepath | varchar(256) | Full path to saved config file |
| backed_up_at | timestamp | UTC timestamp of backup |
| success | boolean | Whether backup succeeded |
| lines | integer | Line count of config |

#### compliance_results table

| Column | Type | Description |
|---|---|---|
| id | integer PK | Auto-increment |
| hostname | varchar(64) | Device name |
| policy | varchar(128) | Policy name checked |
| passed | boolean | Pass or fail |
| detail | text | Human-readable finding |
| checked_at | timestamp | UTC timestamp of check |

### session.py

```python
from src.database.session import init_db, get_session

init_db()           # Creates tables if not exist
session = get_session()  # Returns a new SQLAlchemy session
```

---

## Tasks — src/tasks/

### backup.py — backup_config(task)

Nornir task that:
1. SSHs into device and pulls running config
2. Saves to `configs/{hostname}/{hostname}_{timestamp}.txt`
3. Inserts metadata record into `config_backups` table

Commands per platform:
| Platform | Command |
|---|---|
| linux | `vtysh -c 'show running-config'` |
| cisco_ios | `show running-config` |
| cisco_asa | `show running-config` |

### compliance.py — check_compliance(task)

Nornir task that runs all applicable policies for a device and inserts results into `compliance_results` table.

### facts.py — get_facts(task)

Nornir task that collects hostname, platform, and version info. Used for device inventory enrichment.
