# Scripts

Bootstrap, verification, and runner scripts for the NetOps Automation Hub.

---

## Script Reference

| Script | Purpose |
|---|---|
| `bootstrap.py` | Master bootstrap menu — configures all GNS3 devices |
| `common.py` | Shared helpers, credentials, Netmiko connect wrapper |
| `verify_infra.py` | Verifies PostgreSQL and Redis are reachable |
| `test_connectivity.py` | Verifies Nornir can SSH into all managed devices |
| `run_backup.py` | Runs config backup against all managed devices |
| `run_compliance.py` | Runs compliance checks against all managed devices |

---

## bootstrap.py

Master menu script. Run after every GNS3 restart to restore device runtime config.

```bash
source venv/bin/activate
python3 scripts/bootstrap.py
```

### Menu Options

| Option | Device |
|---|---|
| 1 | FRR-R2 |
| 2 | FRR-R1 |
| 3 | ASA-FW |
| 4 | SW2-L3 |
| 5 | SW1-L2 |
| * | All devices |
| 0 | Quit |

### What bootstrap does per device

**FRR-R1 and FRR-R2:**
- Checks and sets interface IPs
- Verifies default route
- Sets DNS to 8.8.8.8
- Enables IP forwarding
- Sets NAT masquerade (FRR-R2 only, scoped to 10.0.0.0/8)
- Checks static return routes
- Verifies FRR service running
- Checks BGP state
- Sets management loopback 10.0.99.2 (FRR-R2 only)
- Sets return route to 192.168.66.0/24 (FRR-R2 only)

**ASA-FW:**
- Verifies SSH reachability
- Checks interface IPs
- Verifies routes and ACLs
- Saves config with write memory

**SW2-L3 and SW1-L2:**
- Enables ip routing (SW2 only)
- Verifies VLAN and trunk config
- Checks SSH accessibility
- Saves config with write memory

---

## common.py

Shared module imported by all bootstrap scripts.

### Exports

| Name | Type | Description |
|---|---|---|
| `FRR_USER` | str | FRR SSH username from .env |
| `FRR_PASS` | str | FRR SSH password from .env |
| `FRR_R1_HOST` | str | FRR-R1 management IP |
| `FRR_R2_HOST` | str | FRR-R2 loopback IP (10.0.99.2) |
| `CISCO_USER` | str | Cisco SSH username |
| `CISCO_PASS` | str | Cisco SSH password |
| `CISCO_ENABLE` | str | Cisco enable secret |
| `ASA_HOST` | str | ASA management IP |
| `connect()` | func | Netmiko ConnectHandler wrapper |
| `run()` | func | send_command wrapper |
| `run_config()` | func | send_command_timing wrapper |
| `ok/warn/fail/section` | func | Rich console output helpers |

---

## verify_infra.py

Checks PostgreSQL and Redis connectivity before running any automation.

```bash
python3 scripts/verify_infra.py
```

Expected output:
```
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Service          ┃ Status     ┃ Detail                                 ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ PostgreSQL       │ PASS       │ PostgreSQL 14.x                        │
│ Redis            │ PASS       │ Redis 7.x                              │
└──────────────────┴────────────┴────────────────────────────────────────┘
All checks passed.
```

---

## test_connectivity.py

Verifies Nornir can SSH into all 4 managed devices (ASA excluded).

```bash
python3 scripts/test_connectivity.py
```

Expected output — all 4 devices PASS:
```
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Host         ┃ Platform     ┃ Status   ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ frr-r1       │ linux        │ PASS     │
│ frr-r2       │ linux        │ PASS     │
│ sw2-l3       │ cisco_ios    │ PASS     │
│ sw1-l2       │ cisco_ios    │ PASS     │
└──────────────┴──────────────┴──────────┘
```

---

## run_backup.py

Pulls running config from all managed devices, saves to `configs/` and records metadata in PostgreSQL.

```bash
python3 scripts/run_backup.py
```

---

## run_compliance.py

Runs all applicable compliance policies per device and stores results in PostgreSQL.

```bash
python3 scripts/run_compliance.py
```

### Compliance Policies

| Device | Policy | Check |
|---|---|---|
| FRR-R1, FRR-R2 | ssh_enabled | SSH process running |
| FRR-R1, FRR-R2 | bgp_neighbor_state | No neighbor in Active/Idle |
| SW1-L2, SW2-L3 | ssh_enabled | `show ip ssh` returns enabled |
| SW1-L2, SW2-L3 | password_encryption | `service password-encryption` present |
| ASA-FW | Excluded | See docs/ISSUES.md issue #22 |

---

## bootstrap/ Directory

Each file exports a single `bootstrap(results)` function. All scripts are idempotent — safe to run multiple times.

| File | Device |
|---|---|
| `frr_r1.py` | FRR-R1 |
| `frr_r2.py` | FRR-R2 |
| `asa_fw.py` | ASA-FW |
| `sw2_l3.py` | SW2-L3 |
| `sw1_l2.py` | SW1-L2 |
