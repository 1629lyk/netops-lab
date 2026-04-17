# NetOps Automation Hub

## Table of Contents

1. [Project Overview](#project-overview)
2. [Infrastructure Summary](#infrastructure-summary)
3. [Network Topology](#network-topology)
4. [IP Addressing Scheme](#ip-addressing-scheme)
5. [Host Environment Setup](#host-environment-setup)
6. [GNS3 Topology Build](#gns3-topology-build)
7. [Device Configurations](#device-configurations)
   - [FRR-R2 (ISP Router)](#frr-r2-isp-router)
   - [FRR-R1 (Edge Router)](#frr-r1-edge-router)
   - [ASA-FW (Firewall)](#asa-fw-firewall)
   - [SW2-L3 (Distribution Switch)](#sw2-l3-distribution-switch)
   - [SW1-L2 (Access Switch)](#sw1-l2-access-switch)
   - [PC1 and PC2 (Ubuntu Docker Endpoints)](#pc1-and-pc2-ubuntu-docker-endpoints)
8. [Known Issues and Solutions](#known-issues-and-solutions)
9. [Post-Restart Recovery Procedure](#post-restart-recovery-procedure)
10. [Verification Checklist](#verification-checklist)

---

## Project Overview

**Name:** NetOps Automation Hub  
**GNS3 Project Name:** `netops-lab`  
**Goal:** Enterprise-grade network automation portfolio platform targeting NOC, network automation engineer, and network security engineer roles.

**Technology Stack:**
- Automation: Nornir, Netmiko, NAPALM, Scrapli
- API: FastAPI + Uvicorn
- Dashboard: Streamlit
- Database: PostgreSQL + SQLAlchemy
- Task Queue: Redis + Celery
- Language: Python 3.11
- Lab: GNS3 (Ubuntu-based VM on VMware Workstation)
- Automation Server: Ubuntu Server 22.04 LTS (VMware)

**Portfolio Capability Mapping:**

| Capability | Role Targeted | Device |
|---|---|---|
| BGP neighbor monitoring | Automation engineer | FRR-R1 ↔ FRR-R2 |
| OSPF topology collection | All three | FRR-R1, SW2-L3 |
| VLAN provisioning automation | NOC + automation | SW1-L2, SW2-L3 |
| Firewall ACL auditing | Security engineer | ASA-FW |
| Config backup + drift detection | All three | All devices |
| Compliance policy engine | Security + automation | All devices |
| FastAPI task orchestration | Automation engineer | Ubuntu Server |
| Streamlit NOC dashboard | NOC | Ubuntu Server |

---

## Infrastructure Summary

| Component | Platform | RAM | Purpose |
|---|---|---|---|
| Windows 11 Host | Physical | — | Workstation, GNS3 GUI |
| GNS3 VM | VMware | 8 GB | Network simulation |
| Ubuntu Server | VMware | 2 GB | Automation platform |

**VMware Network Adapters on Host:**

| Adapter | Subnet | Purpose |
|---|---|---|
| VMnet1 | 192.168.66.0/24 | Management / host-only |
| VMnet8 | 192.168.254.0/24 | NAT / internet |

---

## Network Topology

```
Cloud-MGMT (VMnet1)          Cloud-NAT (VMnet8)
      |                             |
      | eth0 mgmt                   | eth0 internet
      |                             |
   FRR-R1 ─────────eBGP────────── FRR-R2
   eth2 |                      AS 65002
        |
   ASA-FW
   Gi0/0=outside  Gi0/1=inside
        |
     SW2-L3 (distribution)
     E0/0=uplink  E0/1=trunk
        |
     SW1-L2 (access)
     E0/0=trunk  E0/1=PC1  E0/2=PC2
        |           |
       PC1         PC2
    VLAN10       VLAN20
```

**Data path (internet):**
`PC1/PC2 → SW1 → SW2 → ASA → FRR-R1 → eBGP → FRR-R2 → Cloud-NAT → VMnet8`

**Management path:**
`Ubuntu Server → VMnet1 → Cloud-MGMT → FRR-R1 eth0 → routes to all devices`

---

## IP Addressing Scheme

### Management Plane (VMnet1 — 192.168.66.0/24)

| Device | IP | Interface |
|---|---|---|
| Windows 11 | 192.168.66.1 | VMnet1 adapter |
| Ubuntu Server | 192.168.66.131 | ens33 (static) |
| GNS3 VM | 192.168.66.130 | eth0 |
| FRR-R1 | 192.168.66.101 | eth0 |

### VMnet8 NAT (192.168.254.0/24)

| Device | IP | Interface |
|---|---|---|
| Ubuntu Server | 192.168.254.134 | ens34 (DHCP) |
| GNS3 VM | 192.168.254.133 | eth1 |
| FRR-R2 | 192.168.254.135 | eth0 (static) |

### Lab Data Plane (10.0.0.0/8)

| Subnet | Purpose | Devices |
|---|---|---|
| 10.0.12.0/30 | eBGP link | FRR-R1 eth1 (.1) ↔ FRR-R2 eth1 (.2) |
| 10.0.13.0/30 | R1 → ASA outside | FRR-R1 eth2 (.1) ↔ ASA Gi0/0 (.2) |
| 10.0.14.0/24 | ASA inside → SW2 | ASA Gi0/1 (.1) ↔ SW2 E0/0 (.2) |
| 10.10.0.0/24 | VLAN10 Corporate | SW2 Vlan10 (.1), SW1 Vlan10 (.254), PC1 (.11) |
| 10.20.0.0/24 | VLAN20 Guest | SW2 Vlan20 (.1), PC2 (.11) |

### SSH Reachability from Ubuntu Server

| Device | SSH IP | Path |
|---|---|---|
| FRR-R1 | 192.168.66.101 | VMnet1 direct |
| FRR-R2 | 192.168.254.135 | VMnet8 direct |
| ASA-FW | 10.0.13.2 | Via R1 |
| SW2-L3 | 10.0.14.2 | Via R1 → ASA |
| SW1-L2 | 10.10.0.254 | Via R1 → ASA → SW2 |

---

## Host Environment Setup

### Ubuntu Server — Netplan (Static IP + Lab Routes)

File: `/etc/netplan/50-cloud-init.yaml`

```yaml
network:
  version: 2
  ethernets:
    ens33:
      dhcp4: false
      addresses:
        - 192.168.66.131/24
      routes:
        - to: 10.0.0.0/8
          via: 192.168.66.101
    ens34:
      dhcp4: true
```

**Disable cloud-init from overwriting:**
```bash
sudo bash -c 'echo "network: {config: disabled}" > /etc/cloud/cloud.cfg.d/99-disable-network.cfg'
sudo netplan apply
```

### Ubuntu Server — Software Setup

```bash
# Swap (safety net for 2GB RAM)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Python 3.11
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev -y

# Project directory
mkdir -p ~/netops-automation-hub/{src,inventory,templates,tests,docs,configs,scripts,web}
mkdir -p ~/netops-automation-hub/src/{api,core,tasks,parsers,database,utils}
mkdir -p ~/netops-automation-hub/tests/{unit,integration,test_data}
```

### GNS3 VM — Custom Ubuntu Docker Image

Build a pre-configured Ubuntu image with required packages:

```bash
# On GNS3 VM console
cat > ~/Dockerfile << 'EOF'
FROM gns3/ubuntu:noble

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    openssh-server \
    python3 \
    iputils-ping \
    curl \
    net-tools && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
EOF

docker build -t gns3/ubuntu:noble .
```

---

## GNS3 Topology Build

### Node List

| Node | Template | Role |
|---|---|---|
| FRR-R1 | FRRouting | Edge router, OSPF, BGP AS65001 |
| FRR-R2 | FRRouting | ISP simulation, BGP AS65002 |
| ASA-FW | Cisco ASA 9.8 | Firewall, routing |
| SW2-L3 | i86bi-linux-l3-jk9s-15.0.1 | Distribution, inter-VLAN |
| SW1-L2 | i86bi-linux-l2 | Access layer |
| PC1 | gns3/ubuntu:noble | VLAN10 endpoint |
| PC2 | gns3/ubuntu:noble | VLAN20 endpoint |
| Cloud-MGMT | Cloud | VMnet1 bridge |
| Cloud-NAT | Cloud | VMnet8 bridge |

### Cloud Node Configuration

**Critical — must be set correctly or nothing works:**

- `Cloud-MGMT` → Configure → select **VMware Network Adapter VMnet1** only
- `Cloud-NAT` → Configure → select **VMware Network Adapter VMnet8** only

### Wiring Table

| Link | From | Interface | To | Interface |
|---|---|---|---|---|
| 1 | FRR-R1 | eth0 | Cloud-MGMT | any |
| 2 | FRR-R2 | eth0 | Cloud-NAT | any |
| 3 | FRR-R1 | eth1 | FRR-R2 | eth1 |
| 4 | FRR-R1 | eth2 | ASA-FW | GigabitEthernet0/0 |
| 5 | ASA-FW | GigabitEthernet0/1 | SW2-L3 | Ethernet0/0 |
| 6 | SW2-L3 | Ethernet0/1 | SW1-L2 | Ethernet0/0 |
| 7 | SW1-L2 | Ethernet0/1 | PC1 | eth0 |
| 8 | SW1-L2 | Ethernet0/2 | PC2 | eth0 |

> **Interface naming:** FRR nodes use Linux-style (`eth0`, `eth1`). ASA uses Cisco-style (`GigabitEthernet0/x`). i86bi switches use IOU-style (`Ethernet0/x`). Never assume — always confirm in GNS3 when adding links.

---

## Device Configurations

### FRR-R2 (ISP Router)

**Role:** BGP AS65002, internet source via Cloud-NAT, NAT masquerade for all lab traffic.

**Node type:** FRRouting on Alpine Linux 3.23, FRR version 8.2.2

> **Critical:** FRR Docker containers lose all runtime config on restart. Always reapply after GNS3 restart. Phase 3 bootstrap script automates this.

#### Interface setup (run in shell on every start):

```bash
ip link set eth0 up
ip link set eth1 up
ip addr add 192.168.254.135/24 dev eth0
ip addr add 10.0.12.2/30 dev eth1
ip route add default via 192.168.254.2
echo "nameserver 8.8.8.8" > /etc/resolv.conf
sysctl -w net.ipv4.ip_forward=1
iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
iptables -A FORWARD -i eth1 -o eth0 -j ACCEPT
iptables -A FORWARD -i eth0 -o eth1 -m state --state RELATED,ESTABLISHED -j ACCEPT
rc-service frr restart
```

#### Persistent interface config (`/etc/network/interfaces`):

```
auto lo
iface lo inet loopback

auto eth0
iface eth0 inet static
    address 192.168.254.135
    netmask 255.255.255.0
    gateway 192.168.254.2

auto eth1
iface eth1 inet static
    address 10.0.12.2
    netmask 255.255.255.252
```

#### FRR config (via vtysh):

```
configure terminal
hostname FRR-R2
no ipv6 forwarding
!
interface eth0
 description CLOUD-NAT-INTERNET
!
interface eth1
 description LINK-TO-FRR-R1
 ip address 10.0.12.2/30
!
router bgp 65002
 bgp router-id 10.0.12.2
 neighbor 10.0.12.1 remote-as 65001
 neighbor 10.0.12.1 description FRR-R1
 address-family ipv4 unicast
  network 0.0.0.0/0
  neighbor 10.0.12.1 activate
  neighbor 10.0.12.1 default-originate
  neighbor 10.0.12.1 route-map PERMIT-ALL in
  neighbor 10.0.12.1 route-map PERMIT-ALL out
 exit-address-family
!
route-map PERMIT-ALL permit 10
!
ip route 0.0.0.0/0 192.168.254.2
!
ip route 10.0.13.0/30 10.0.12.1
ip route 10.0.14.0/24 10.0.12.1
ip route 10.10.0.0/24 10.0.12.1
ip route 10.20.0.0/24 10.0.12.1
!
end
write memory
```

---

### FRR-R1 (Edge Router)

**Role:** BGP AS65001, OSPF area 0, management gateway, routes lab traffic to internet via R2.

**Node type:** FRRouting on Alpine Linux 3.23, FRR version 8.2.2

#### Interface setup (run in shell on every start):

```bash
ip link set eth0 up
ip link set eth1 up
ip link set eth2 up
ip addr add 192.168.66.101/24 dev eth0
ip addr add 10.0.12.1/30 dev eth1
ip addr add 10.0.13.1/30 dev eth2
sysctl -w net.ipv4.ip_forward=1
echo "nameserver 8.8.8.8" > /etc/resolv.conf
rc-service frr restart
```

#### Persistent interface config (`/etc/network/interfaces`):

```
auto lo
iface lo inet loopback

auto eth0
iface eth0 inet static
    address 192.168.66.101
    netmask 255.255.255.0

auto eth1
iface eth1 inet static
    address 10.0.12.1
    netmask 255.255.255.252

auto eth2
iface eth2 inet static
    address 10.0.13.1
    netmask 255.255.255.252
```

#### FRR config (via vtysh):

```
configure terminal
hostname FRR-R1
no ipv6 forwarding
!
interface eth0
 description MGMT-TO-UBUNTU
 ip address 192.168.66.101/24
!
interface eth1
 description LINK-TO-FRR-R2
 ip address 10.0.12.1/30
!
interface eth2
 description LINK-TO-ASA-OUTSIDE
 ip address 10.0.13.1/30
!
router bgp 65001
 bgp router-id 10.0.12.1
 neighbor 10.0.12.2 remote-as 65002
 neighbor 10.0.12.2 description FRR-R2-ISP
 address-family ipv4 unicast
  neighbor 10.0.12.2 activate
  neighbor 10.0.12.2 route-map PERMIT-ALL in
  neighbor 10.0.12.2 route-map PERMIT-ALL out
  redistribute ospf
 exit-address-family
!
route-map PERMIT-ALL permit 10
!
router ospf
 ospf router-id 10.0.13.1
 redistribute bgp
 default-information originate always
 network 10.0.13.0/30 area 0
 network 192.168.66.0/24 area 0
!
ip route 192.168.66.0/24 eth0
ip route 10.0.14.0/24 10.0.13.2
ip route 10.10.0.0/24 10.0.13.2
ip route 10.20.0.0/24 10.0.13.2
!
end
write memory
```

---

### ASA-FW (Firewall)

**Role:** Firewall between R1 and SW2-L3. Currently in Option A mode (routing only — full policy in Phase 3).

**Node type:** Cisco ASA 9.8.3 (GNS3 virtual)  
**SSH:** Legacy algorithms required — see known issues

> **Critical:** ASA takes 2–4 minutes to fully boot. Never connect via Netmiko before boot completes.

#### Full configuration:

```
enable
configure terminal

hostname ASA-FW

interface GigabitEthernet0/0
 nameif outside
 security-level 0
 ip address 10.0.13.2 255.255.255.252
 no shutdown

interface GigabitEthernet0/1
 nameif inside
 security-level 100
 ip address 10.0.14.1 255.255.255.0
 no shutdown

route outside 0.0.0.0 0.0.0.0 10.0.13.1 1
route inside 10.10.0.0 255.255.255.0 10.0.14.2
route inside 10.20.0.0 255.255.255.0 10.0.14.2

same-security-traffic permit inter-interface

access-list OUTSIDE_IN extended permit ip any any
access-list INSIDE_OUT extended permit ip any any
access-group OUTSIDE_IN in interface outside
access-group INSIDE_OUT in interface inside

policy-map global_policy
 class inspection_default
  inspect icmp
service-policy global_policy global

object network INSIDE_NETS
 subnet 10.0.0.0 255.0.0.0
object network ANY_DEST
 subnet 0.0.0.0 0.0.0.0
nat (inside,outside) source static INSIDE_NETS INSIDE_NETS destination static ANY_DEST ANY_DEST

crypto key generate rsa modulus 2048
ssh 192.168.66.0 255.255.255.0 outside
ssh 10.0.0.0 255.0.0.0 outside
ssh version 2
ssh timeout 60

username netops password NetOps2024! privilege 15
aaa authentication ssh console LOCAL
enable password NetOps2024!

terminal pager 0

write memory
```

> **After every restart:** ACL and NAT rules persist via `write memory` on ASA. However verify with `show access-group` and `show route` after boot.

#### SSH config on Ubuntu Server (`~/.ssh/config`):

```
Host 10.0.13.2
    KexAlgorithms diffie-hellman-group1-sha1
    HostKeyAlgorithms ssh-rsa
    Ciphers aes128-cbc,aes256-cbc,3des-cbc
```

---

### SW2-L3 (Distribution Switch)

**Role:** Inter-VLAN routing, distribution layer, OSPF participant.

**Node type:** i86bi-linux-l3-jk9s-15.0.1 (IOU L3, full enterprise feature set)  
**Interface naming:** `Ethernet0/x` (IOU style, not GigabitEthernet)

```
enable
configure terminal

hostname SW2-L3
ip routing

interface Ethernet0/0
 description UPLINK-TO-ASA-INSIDE
 no switchport
 ip address 10.0.14.2 255.255.255.0
 no shutdown

interface Ethernet0/1
 description TRUNK-TO-SW1-L2
 switchport trunk encapsulation dot1q
 switchport mode trunk
 no shutdown

vlan 10
 name CORPORATE
vlan 20
 name GUEST

interface Vlan10
 description CORPORATE-USERS
 ip address 10.10.0.1 255.255.255.0
 no shutdown

interface Vlan20
 description GUEST-USERS
 ip address 10.20.0.1 255.255.255.0
 no shutdown

ip route 0.0.0.0 0.0.0.0 10.0.14.1

router ospf 1
 router-id 10.0.14.2
 network 10.0.14.0 0.0.0.255 area 0
 network 10.10.0.0 0.0.0.255 area 0
 network 10.20.0.0 0.0.0.255 area 0

ip domain-name netops-lab.local
crypto key generate rsa modulus 2048
username netops privilege 15 secret NetOps2024!
line vty 0 4
 login local
 transport input ssh
ip ssh version 2

end
write memory
```

---

### SW1-L2 (Access Switch)

**Role:** Access layer, VLAN10 and VLAN20 to endpoints, managed via VLAN10 SVI.

**Node type:** i86bi-linux-l2 (IOU L2)  
**Interface naming:** `Ethernet0/x`

```
enable
configure terminal

hostname SW1-L2
no ip routing

interface Ethernet0/0
 description TRUNK-TO-SW2-L3
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk allowed vlan 1,10,20
 no shutdown

interface Ethernet0/1
 description ACCESS-PC1
 switchport mode access
 switchport access vlan 10
 no shutdown

interface Ethernet0/2
 description ACCESS-PC2
 switchport mode access
 switchport access vlan 20
 no shutdown

vlan 10
 name CORPORATE
vlan 20
 name GUEST

interface Vlan10
 ip address 10.10.0.254 255.255.255.0
 no shutdown

ip default-gateway 10.10.0.1

ip domain-name netops-lab.local
crypto key generate rsa modulus 2048
username netops privilege 15 secret NetOps2024!
line vty 0 4
 login local
 transport input ssh
ip ssh version 2

end
write memory
```

---

### PC1 and PC2 (Ubuntu Docker Endpoints)

**Image:** `gns3/ubuntu:noble` (custom build with packages pre-installed)  
**PC1:** VLAN10 — 10.10.0.11/24  
**PC2:** VLAN20 — 10.20.0.11/24

> **Critical:** Docker containers lose runtime network config on restart. Apply on every start or write a startup script.

**PC1 (run on every start):**

```bash
ip link set eth0 mtu 1500
ip addr add 10.10.0.11/24 dev eth0
ip link set eth0 up
ip route add default via 10.10.0.1
echo "nameserver 8.8.8.8" > /etc/resolv.conf
```

**PC2 (run on every start):**

```bash
ip link set eth0 mtu 1500
ip addr add 10.20.0.11/24 dev eth0
ip link set eth0 up
ip route add default via 10.20.0.1
echo "nameserver 8.8.8.8" > /etc/resolv.conf
```

**Installed packages:** openssh-server, python3, iputils-ping, curl, net-tools

---

## Known Issues and Solutions

### 1. FRR Docker containers lose config on restart
**Symptom:** After GNS3 restart, FRR-R1 and FRR-R2 have no IPs, no routes, BGP down.  
**Cause:** FRR runs as a Docker container in GNS3. Runtime interface config (`ip addr`, `ip route`, `iptables`) is not persisted by default.  
**Solution:** Reapply interface config manually or use Phase 3 bootstrap script. FRR routing config (`frr.conf`) does persist via `write memory`.

### 2. FRR 8.x BGP denies all prefixes by default
**Symptom:** BGP session shows `Established` but `PfxRcd` and `PfxSnt` show `(Policy)`.  
**Cause:** FRR 8.x introduced a deny-all default BGP policy unlike older versions.  
**Solution:** Apply explicit route-map on both peers:
```
route-map PERMIT-ALL permit 10
neighbor X.X.X.X route-map PERMIT-ALL in
neighbor X.X.X.X route-map PERMIT-ALL out
```

### 3. udhcpc fails on FRR-R2 eth0
**Symptom:** `udhcpc: failed to get a DHCP lease` when trying to get internet via Cloud-NAT.  
**Cause:** Cloud-NAT bridges to the GNS3 VM's own VMnet8 NIC. VMware's DHCP won't issue a second lease to the container through the bridge.  
**Solution:** Assign static IP `192.168.254.135/24` with gateway `192.168.254.2` (VMware NAT gateway is always `.2`).

### 4. FRR apk package manager fails
**Symptom:** `ERROR: http://dl-cdn.alpinelinux.org/alpine/v3.16/main: temporary error`  
**Cause:** FRR image declares wrong Alpine version in repo URLs, or DNS not set.  
**Solution:**
```bash
echo "nameserver 8.8.8.8" > /etc/resolv.conf
cat > /etc/apk/repositories << 'EOF'
https://dl-cdn.alpinelinux.org/alpine/v3.23/main
https://dl-cdn.alpinelinux.org/alpine/v3.23/community
EOF
apk update
```

### 5. ASA SSH key exchange failure
**Symptom:** `no matching key exchange method found. Their offer: diffie-hellman-group1-sha1`  
**Cause:** ASA 9.8 only supports legacy SSH algorithms that modern OpenSSH disables by default.  
**Solution:** Add to `~/.ssh/config` on Ubuntu Server:
```
Host 10.0.13.2
    KexAlgorithms diffie-hellman-group1-sha1
    HostKeyAlgorithms ssh-rsa
    Ciphers aes128-cbc,aes256-cbc,3des-cbc
```
Also required in Netmiko device parameters for ASA.

### 6. ASA `route mgmt` conflict error
**Symptom:** `ERROR: Cannot add route entry, conflict with existing routes`  
**Cause:** Management0/0 already has a connected route for the management subnet. ASA rejects a default route out the same interface.  
**Solution:** Use a specific host route instead:
```
route mgmt 192.168.66.131 255.255.255.255 192.168.66.1 1
```

### 7. ASA drops traffic from inside to VLAN subnets
**Symptom:** SW2-L3 can ping ASA inside (10.0.14.1) but not internet. tcpdump on R1 shows requests and replies passing but SW2 never gets them.  
**Cause:** ASA had no route for VLAN subnets (10.10.0.0/24, 10.20.0.0/24) on the inside interface.  
**Solution:**
```
route inside 10.10.0.0 255.255.255.0 10.0.14.2
route inside 10.20.0.0 255.255.255.0 10.0.14.2
```

### 8. Duplicate ICMP packets on FRR-R1 eth2
**Symptom:** tcpdump shows every packet appearing twice on eth2.  
**Cause:** Routing loop — R1 forwards packet to ASA, ASA returns it back to R1 outside interface.  
**Solution:** Ensure ASA has correct `route inside` entries so it doesn't send traffic back upstream.

### 9. Cloud-MGMT must bind to specific VMware adapter
**Symptom:** Management devices unreachable even though Cloud-MGMT is configured.  
**Cause:** Cloud node bound to wrong interface (e.g. physical NIC instead of VMnet1).  
**Solution:** Right-click Cloud-MGMT → Configure → select **VMware Network Adapter VMnet1** explicitly.

### 10. Ubuntu Server routes lost on restart
**Symptom:** After reboot, `ping 192.168.66.101` fails from Ubuntu.  
**Cause:** ens33 was on DHCP via cloud-init which doesn't persist manual routes.  
**Solution:** Set static IP in Netplan and disable cloud-init network management:
```bash
sudo bash -c 'echo "network: {config: disabled}" > /etc/cloud/cloud.cfg.d/99-disable-network.cfg'
```

### 11. i86bi-L2 has IP routing enabled by default
**Symptom:** L2 switch behaves like a router, unexpected routing behavior.  
**Solution:** Always add `no ip routing` in SW1-L2 config.

### 12. i86bi-L3 uses Ethernet0/x not GigabitEthernet
**Symptom:** Interface commands fail on SW2-L3.  
**Cause:** IOU images use `Ethernet0/x` naming, not `GigabitEthernet`.  
**Solution:** Always use `Ethernet0/0`, `Ethernet0/1` etc. on IOU-based nodes.

### 13. Docker container name conflict on GNS3 restart
**Symptom:** `Docker has returned an error: 409 Conflict. The container name is already in use`  
**Cause:** GNS3 crashed or didn't shut down cleanly, leaving orphaned Docker containers.  
**Solution:** On GNS3 VM console:
```bash
docker ps -a | grep GNS3 | awk '{print $1}' | xargs docker stop
docker ps -a | grep GNS3 | awk '{print $1}' | xargs docker rm
```
**Prevention:** Always stop all nodes in GNS3 before closing project.

### 14. Ubuntu Docker PC apt fails — unable to locate package
**Symptom:** `E: Unable to locate package openssh-server` on fresh Docker container.  
**Cause:** Package lists not populated on fresh container.  
**Solution:** Run `apt-get update` first. For speed use `--no-install-recommends`.  
**Better solution:** Pre-bake packages into the Docker image using a custom Dockerfile.

### 15. FRR-R1 has no route to VLAN subnets
**Symptom:** Ubuntu can reach ASA (10.0.13.2) but not SW2 VLANs (10.10.0.1, 10.20.0.1).  
**Cause:** R1 only had a static route to 10.0.14.0/24 but not to VLAN subnets behind SW2.  
**Solution:** Add on FRR-R1:
```bash
vtysh -c "conf t"
ip route 10.10.0.0/24 10.0.13.2
ip route 10.20.0.0/24 10.0.13.2
```

### 16. ASA NAT syntax error in 9.8
**Symptom:** `ERROR: any doesn't match an existing object or object-group`  
**Cause:** ASA 9.8 requires named network objects for NAT — `any` keyword not supported directly.  
**Solution:** Define objects first:
```
object network INSIDE_NETS
 subnet 10.0.0.0 255.0.0.0
object network ANY_DEST
 subnet 0.0.0.0 0.0.0.0
nat (inside,outside) source static INSIDE_NETS INSIDE_NETS destination static ANY_DEST ANY_DEST
```

---

## Post-Restart Recovery Procedure

Run this procedure every time GNS3 is restarted. Phase 3 bootstrap script will automate this entirely.

### Step 1 — Fix Docker conflicts (if any)
```bash
# On GNS3 VM
docker ps -a | grep GNS3 | awk '{print $1}' | xargs docker stop 2>/dev/null
docker ps -a | grep GNS3 | awk '{print $1}' | xargs docker rm 2>/dev/null
```

### Step 2 — Start all nodes in GNS3 GUI
Wait for all nodes to show green. ASA takes 2–4 minutes.

### Step 3 — Restore FRR-R2
```bash
ip link set eth0 up && ip link set eth1 up
ip addr add 192.168.254.135/24 dev eth0
ip addr add 10.0.12.2/30 dev eth1
ip route add default via 192.168.254.2
echo "nameserver 8.8.8.8" > /etc/resolv.conf
sysctl -w net.ipv4.ip_forward=1
iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
iptables -A FORWARD -i eth1 -o eth0 -j ACCEPT
iptables -A FORWARD -i eth0 -o eth1 -m state --state RELATED,ESTABLISHED -j ACCEPT
rc-service frr restart
```

### Step 4 — Restore FRR-R1
```bash
ip link set eth0 up && ip link set eth1 up && ip link set eth2 up
ip addr add 192.168.66.101/24 dev eth0
ip addr add 10.0.12.1/30 dev eth1
ip addr add 10.0.13.1/30 dev eth2
sysctl -w net.ipv4.ip_forward=1
rc-service frr restart
```

### Step 5 — Verify BGP (wait 15 seconds after FRR restart)
```bash
# On FRR-R1
vtysh -c "show bgp summary"
# Expected: State/PfxRcd = 1, Up/Down shows uptime
```

### Step 6 — Restore ASA ACLs (if lost)
```
access-list OUTSIDE_IN extended permit ip any any
access-list INSIDE_OUT extended permit ip any any
access-group OUTSIDE_IN in interface outside
access-group INSIDE_OUT in interface inside
route inside 10.10.0.0 255.255.255.0 10.0.14.2
route inside 10.20.0.0 255.255.255.0 10.0.14.2
write memory
```

### Step 7 — Restore PC1 and PC2
```bash
# PC1
ip link set eth0 mtu 1500
ip addr add 10.10.0.11/24 dev eth0
ip link set eth0 up
ip route add default via 10.10.0.1
echo "nameserver 8.8.8.8" > /etc/resolv.conf

# PC2
ip link set eth0 mtu 1500
ip addr add 10.20.0.11/24 dev eth0
ip link set eth0 up
ip route add default via 10.20.0.1
echo "nameserver 8.8.8.8" > /etc/resolv.conf
```

---

## Verification Checklist

Run from Ubuntu Server after every restart to confirm full lab health:

```bash
echo "=== Routed plane reachability ==="
for ip in 192.168.66.101 192.168.254.135 10.0.13.2 10.0.14.2 10.10.0.1 10.10.0.254 10.20.0.1; do
  ping -c2 -W2 $ip > /dev/null 2>&1 \
    && echo "PASS $ip" \
    || echo "FAIL $ip"
done

echo ""
echo "=== SSH connectivity ==="
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
    netops@192.168.66.101 "hostname" 2>/dev/null \
  && echo "SSH PASS FRR-R1" || echo "SSH FAIL FRR-R1"

ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
    netops@192.168.254.135 "hostname" 2>/dev/null \
  && echo "SSH PASS FRR-R2" || echo "SSH FAIL FRR-R2"

ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
    -o KexAlgorithms=diffie-hellman-group1-sha1 \
    -o HostKeyAlgorithms=ssh-rsa \
    -o Ciphers=aes128-cbc,aes256-cbc,3des-cbc \
    netops@10.0.13.2 "show hostname" 2>/dev/null \
  && echo "SSH PASS ASA-FW" || echo "SSH FAIL ASA-FW"

ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
    netops@10.0.14.2 "show hostname" 2>/dev/null \
  && echo "SSH PASS SW2-L3" || echo "SSH FAIL SW2-L3"

ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
    netops@10.10.0.254 "show hostname" 2>/dev/null \
  && echo "SSH PASS SW1-L2" || echo "SSH FAIL SW1-L2"

echo ""
echo "=== GNS3 API ==="
curl -s http://192.168.254.133:3080/v2/version | python3 -m json.tool

echo ""
echo "=== Internet ==="
ping -c2 -W2 8.8.8.8 > /dev/null 2>&1 \
  && echo "PASS internet" || echo "FAIL internet"
```

**Expected results — all PASS, GNS3 API returns JSON version, internet reachable.**
