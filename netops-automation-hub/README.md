# NetOps Automation Hub

An enterprise-grade network automation platform built on a real GNS3 lab environment. Targets NOC, network automation engineer, and network security engineer roles.

Automates config backup, compliance checking, device monitoring, and NOC dashboarding across a 5-node lab running Cisco IOS, Cisco ASA, FRRouting, and Linux.

---

## Platform Overview

| Component | Technology |
|---|---|
| Language | Python 3.11 |
| Automation Engine | Nornir 3.5 + Netmiko 4.6 |
| REST API | FastAPI 0.136 + Uvicorn 0.44 |
| NOC Dashboard | Streamlit 1.56 |
| Database | PostgreSQL 14 + SQLAlchemy 2.0 |
| Cache | Redis 7 |
| Config Templating | Jinja2 3.1 |
| Containers | Docker + Docker Compose v2 |
| Lab Platform | GNS3 VM on VMware Workstation |
| Host OS | Windows 11 |

---

## Lab Topology

```
[Ubuntu Server 192.168.66.131]
        |
    VMnet1 (192.168.66.0/24) — Management
        |
    [FRR-R1 192.168.66.101] — BGP AS65001
        |--- eth1 10.0.12.1 --- [FRR-R2 10.0.99.2] --- Cloud-NAT --- Internet
        |--- eth2 10.0.13.1 --- [ASA-FW 10.0.13.2]
                                        |
                                [SW2-L3 10.0.14.2]
                                        |
                                [SW1-L2 10.10.0.254]
                                   |         |
                               [PC1]       [PC2]
                            VLAN10       VLAN20
```

### Node Reference

| Node | Platform | SSH IP | Role |
|---|---|---|---|
| FRR-R1 | FRRouting 8.2.2 / Alpine | 192.168.66.101 | Core router, BGP AS65001, OSPF |
| FRR-R2 | FRRouting 8.2.2 / Alpine | 10.0.99.2 (loopback) | ISP simulator, BGP AS65002 |
| ASA-FW | Cisco ASA 9.8.3 (unlicensed) | 10.0.13.2 | Edge firewall — bootstrap only |
| SW2-L3 | IOU L3 i86bi 15.0.1 | 10.0.14.2 | Distribution L3 switch |
| SW1-L2 | IOU L2 i86bi 15.1 | 10.10.0.254 | Access L2 switch |

> ASA is excluded from automated Nornir tasks due to unlicensed SSH instability. It is managed via the bootstrap script only. See [docs/ISSUES.md](docs/ISSUES.md).

---

## IP Addressing

| Subnet | Purpose |
|---|---|
| 192.168.66.0/24 | VMnet1 — host-only management |
| 192.168.254.0/24 | VMnet8 — NAT / internet |
| 10.0.12.0/30 | eBGP link FRR-R1 ↔ FRR-R2 |
| 10.0.13.0/30 | FRR-R1 eth2 ↔ ASA outside |
| 10.0.14.0/24 | ASA inside ↔ SW2-L3 |
| 10.10.0.0/24 | VLAN10 — Corporate |
| 10.20.0.0/24 | VLAN20 — Guest |
| 10.0.99.2/32 | FRR-R2 management loopback |

---

## Quick Start

### Prerequisites
- GNS3 VM running with `netops-lab` project open and all nodes started
- Ubuntu Server 22.04 at `192.168.66.131`
- Docker and Docker Compose v2 installed

### 1. Set up Python environment
```bash
cd ~/netops-automation-hub
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure credentials
```bash
cp .env.example .env
# Edit .env and fill in all credentials
```

### 3. Start Docker services
```bash
sudo docker compose up -d
sudo docker compose ps
```

### 4. Initialize database
```bash
python3 -c "from src.database.session import init_db; init_db(); print('Tables created')"
```

### 5. Bootstrap all lab devices
```bash
python3 scripts/bootstrap.py
# Select * to bootstrap all devices
```

### 6. Verify connectivity
```bash
python3 scripts/verify_infra.py
python3 scripts/test_connectivity.py
```

### 7. Run automation tasks
```bash
python3 scripts/run_backup.py
python3 scripts/run_compliance.py
```

### 8. Start API server
```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 9. Start NOC dashboard
```bash
streamlit run web/dashboard.py --server.port 8501 --server.address 0.0.0.0
```

### Access Points
| Service | URL |
|---|---|
| REST API | http://192.168.66.131:8000 |
| Swagger UI | http://192.168.66.131:8000/docs |
| NOC Dashboard | http://192.168.66.131:8501 |

---

## Project Structure

```
netops-automation-hub/
├── README.md                        # This file
├── .env                             # Credentials — never commit
├── .env.example                     # Credential template
├── requirements.txt                 # Pinned Python dependencies
├── docker-compose.yml               # PostgreSQL + Redis
├── configs/                         # Device config backups
│   └── README.md
├── docs/
│   └── ISSUES.md                    # Known issues and fixes
├── inventory/                       # Nornir YAML inventory
│   └── README.md
├── scripts/                         # Bootstrap and runner scripts
│   └── README.md
├── src/                             # Core application code
│   ├── api/                         # FastAPI routers
│   ├── core/                        # Nornir engine
│   ├── database/                    # SQLAlchemy models + session
│   ├── tasks/                       # Nornir automation tasks
│   ├── parsers/                     # TextFSM/Genie parsers
│   └── README.md
├── templates/                       # Jinja2 config templates
│   └── README.md
├── tests/                           # pytest test suite
│   └── README.md
└── web/                             # Streamlit NOC dashboard
    └── README.md
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | API, database, Redis status |
| GET | `/devices` | All devices with live reachability |
| GET | `/configs` | All config backup records |
| POST | `/configs/backup` | Trigger backup on all devices |
| GET | `/compliance` | All compliance check results |
| POST | `/compliance/run` | Trigger compliance check on all devices |

---

## Portfolio Capability Mapping

| Capability | Role Targeted | Device |
|---|---|---|
| BGP neighbor monitoring + route validation | Automation engineer | FRR-R1, FRR-R2 |
| Config backup + drift detection | All three | FRR-R1, FRR-R2, SW2-L3, SW1-L2 |
| Compliance policy engine | Security + automation | FRR-R1, FRR-R2, SW2-L3, SW1-L2 |
| VLAN + trunk automation | NOC + automation | SW1-L2, SW2-L3 |
| Firewall ACL auditing | Security engineer | ASA-FW (bootstrap only) |
| FastAPI REST orchestration | Automation engineer | Ubuntu Server |
| Streamlit NOC dashboard | NOC | Ubuntu Server |
| PostgreSQL persistent state | All three | Ubuntu Server |

---

## Known Issues

See [docs/ISSUES.md](docs/ISSUES.md) for the full list of issues encountered and resolved during this build.

---

## Environment Variables

See [.env.example](.env.example) for the full list of required environment variables.
