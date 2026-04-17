# Configs

Device configuration backups pulled by the automation engine.

---

## Directory Structure

```
configs/
├── frr-r1/
│   ├── frr-r1_20260416_192512.txt
│   └── frr-r1_20260416_201030.txt
├── frr-r2/
│   └── frr-r2_20260416_192512.txt
├── sw2-l3/
│   └── sw2-l3_20260416_192512.txt
└── sw1-l2/
    └── sw1-l2_20260416_192512.txt
```

One subdirectory per device. Multiple timestamped files accumulate over time — full backup history is preserved.

---

## File Naming

```
{hostname}_{YYYYMMDD}_{HHMMSS}.txt
```

Example: `frr-r1_20260416_192512.txt` — FRR-R1 backup taken on April 16 2026 at 19:25:12 UTC.

---

## How Backups Are Triggered

### Manual via script
```bash
python3 scripts/run_backup.py
```

### Manual via API
```bash
curl -X POST http://192.168.66.131:8000/configs/backup
```

### Manual via dashboard
Click **Run Backup Now** button in the Streamlit NOC dashboard.

---

## Backup Metadata

Every backup run inserts a record into the `config_backups` PostgreSQL table:

| Field | Description |
|---|---|
| hostname | Device name |
| filepath | Full path to the saved .txt file |
| backed_up_at | UTC timestamp |
| success | True/False |
| lines | Line count of the config |

Query recent backups:
```bash
sudo docker exec -it netops_postgres psql -U netops -d netops_hub \
  -c "SELECT hostname, backed_up_at, lines, success FROM config_backups ORDER BY backed_up_at DESC LIMIT 10;"
```

---

## Devices Backed Up

| Device | Platform | Config command |
|---|---|---|
| frr-r1 | FRRouting | `vtysh -c 'show running-config'` |
| frr-r2 | FRRouting | `vtysh -c 'show running-config'` |
| sw2-l3 | Cisco IOS | `show running-config` |
| sw1-l2 | Cisco IOS | `show running-config` |

> ASA-FW is excluded from automated backups. See [../docs/ISSUES.md](../docs/ISSUES.md) issue #22.

---

## Notes

- Files are never overwritten — each run creates a new timestamped file
- This directory is excluded from `.gitignore` to avoid committing device configs to version control
- Backup history accumulates indefinitely — implement a retention policy for long-running deployments
