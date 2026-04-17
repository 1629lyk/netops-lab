# Inventory

Nornir YAML inventory for all managed network devices.

---

## Files

| File | Purpose |
|---|---|
| `hosts.yaml` | Device definitions — IPs, groups, metadata |
| `groups.yaml` | Platform settings and SSH options per group |
| `defaults.yaml` | Global defaults applied to all hosts |

---

## Device Inventory

| Hostname | IP | Group | Role | Automated |
|---|---|---|---|---|
| frr-r1 | 192.168.66.101 | frr | Core router | Yes |
| frr-r2 | 10.0.99.2 | frr | ISP simulator | Yes |
| asa-fw | 10.0.13.2 | cisco_asa | Firewall | No (bootstrap only) |
| sw2-l3 | 10.0.14.2 | cisco_ios | L3 switch | Yes |
| sw1-l2 | 10.10.0.254 | cisco_ios | L2 switch | Yes |

> ASA has `exclude_from_automation: true` in hosts.yaml — excluded from Nornir backup and compliance tasks due to unlicensed SSH instability. See [../docs/ISSUES.md](../docs/ISSUES.md) issue #22.

---

## Groups

### frr
- Platform: `linux`
- Netmiko device_type: resolved from platform
- SSH timeout: 30s

### cisco_ios
- Platform: `cisco_ios`
- global_delay_factor: 2 (IOU images are slow to respond)
- SSH timeout: 30s

### cisco_asa
- Platform: `cisco_asa`
- global_delay_factor: 2
- ssh_config_file: `~/.ssh/config` (required for legacy algorithm negotiation)
- SSH timeout: 30s

---

## Credential Injection

**Credentials are never stored in YAML files.**

`src/core/engine.py` loads credentials from `.env` at runtime and injects them into each host object based on group membership. This means `hosts.yaml` and `groups.yaml` are safe to commit to version control.

### How it works

```
.env loaded → _inject_credentials() loops hosts → assigns credentials by group → Nornir ready
```

---

## Excluding Devices from Automation

To exclude a device from Nornir automated tasks (backup, compliance), add to its `hosts.yaml` entry:

```yaml
data:
  exclude_from_automation: true
```

`get_nornir_managed()` in `src/core/engine.py` filters these devices out automatically. The device still appears in `GET /devices` for visibility.

---

## Adding a New Device

1. Add entry to `hosts.yaml` with hostname, IP, group, and data fields
2. Ensure the device's platform group exists in `groups.yaml`
3. Add credentials to `.env` if using a new credential set
4. Run `python3 scripts/test_connectivity.py` to verify
