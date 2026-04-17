# Known Issues and Fixes

All issues encountered during the build of NetOps Automation Hub, with root cause analysis and applied fixes.

---

## 1. FRR 8.x BGP deny-all default policy

**Symptom:** BGP sessions established at TCP level but no routes exchanged.  
**Root cause:** FRR 8.x ships with an implicit deny-all BGP policy.  
**Fix:** Apply `route-map PERMIT-ALL permit 10` on both neighbors in both directions on both peers.

---

## 2. FRR Docker containers lose runtime config on restart

**Symptom:** Interface IPs, static routes, and iptables rules disappear after GNS3 restart.  
**Root cause:** FRR nodes are Docker containers — runtime config is not persisted. `frr.conf` survives but kernel networking state does not.  
**Fix:** Bootstrap script restores all runtime config automatically on each run.

---

## 3. FRR-R2 DHCP fails via Cloud-NAT

**Symptom:** FRR-R2 cannot get DHCP lease on eth0 via VMnet8.  
**Root cause:** VMware will not issue a second DHCP lease to a VM on the same VMnet8 segment as the GNS3 VM.  
**Fix:** Static IP `192.168.254.135/24`, gateway `192.168.254.2` (VMware NAT gateway is always `.2`).

---

## 4. FRR apk package repos fail

**Symptom:** `apk add` fails with repo errors.  
**Root cause:** Incorrect Alpine version in `/etc/apk/repositories`.  
**Fix:** Set correct Alpine version in repos and run `echo "nameserver 8.8.8.8" > /etc/resolv.conf` first.

---

## 5. ASA SSH legacy algorithm rejection

**Symptom:** SSH to ASA fails with `no matching key exchange method`.  
**Root cause:** ASA 9.8 only supports `diffie-hellman-group1-sha1`.  
**Fix:** Add to `~/.ssh/config`:
```
Host 10.0.13.2
    KexAlgorithms diffie-hellman-group1-sha1
    HostKeyAlgorithms ssh-rsa
    Ciphers aes128-cbc,aes256-cbc,3des-cbc
```
Also required in Netmiko connection params for ASA group in inventory.

---

## 6. ASA route management conflict error

**Symptom:** `Cannot add route entry, conflict with existing routes` on ASA.  
**Root cause:** Default route via management interface conflicts with static route.  
**Fix:** Use specific host routes instead of default via mgmt interface.

---

## 7. ASA drops traffic — missing inside routes

**Symptom:** Traffic from lab VLANs cannot reach internet.  
**Root cause:** ASA had no routes for `10.10.0.0/24` and `10.20.0.0/24` on inside interface.  
**Fix:** Added `route inside 10.10.0.0 255.255.255.0 10.0.14.2` and `route inside 10.20.0.0 255.255.255.0 10.0.14.2`.

---

## 8. ASA NAT syntax error

**Symptom:** NAT config rejected with syntax error.  
**Root cause:** `any` keyword not supported in ASA 9.8 NAT syntax.  
**Fix:** Use named network objects instead of `any`.

---

## 9. IOU L2 has IP routing enabled by default

**Symptom:** SW1-L2 routing traffic instead of switching.  
**Root cause:** `i86bi-linux-l2` image has `ip routing` enabled by default.  
**Fix:** Always add `no ip routing` to SW1-L2 config.

---

## 10. IOU uses Ethernet0/x not GigabitEthernet

**Symptom:** Interface config rejected on IOU nodes.  
**Root cause:** IOU images use `Ethernet0/x` naming, not `GigabitEthernet`.  
**Fix:** Always use `Ethernet0/x` on IOU L2 and L3 nodes.

---

## 11. Docker 409 conflict on GNS3 restart

**Symptom:** GNS3 nodes fail to start after restart with 409 conflict.  
**Root cause:** Orphaned Docker containers from previous session.  
**Fix:**
```bash
docker ps -a | grep GNS3 | awk '{print $1}' | xargs docker stop
docker ps -a | grep GNS3 | awk '{print $1}' | xargs docker rm
```

---

## 12. Ubuntu Server cloud-init overwrites Netplan

**Symptom:** Static IP config lost after reboot.  
**Root cause:** cloud-init regenerates network config on boot.  
**Fix:** Disable cloud-init network management:
```bash
echo "network: {config: disabled}" > /etc/cloud/cloud.cfg.d/99-disable-network.cfg
```

---

## 13. SW2-L3 ip routing disabled after restart

**Symptom:** SW2-L3 stops routing after GNS3 restart.  
**Root cause:** IOS saves `ip routing` via `write memory` but sometimes loses it on IOU restart.  
**Fix:** Bootstrap script checks and reapplies `ip routing` on every run.

---

## 14. FRR-R1 asymmetric routing for 10.0.12.0/30

**Symptom:** Ubuntu cannot ping FRR-R2 eBGP link IP `10.0.12.2`.  
**Root cause:** Reply from FRR-R2 goes out wrong interface, causing asymmetric routing.  
**Fix:** Use FRR-R2's loopback `10.0.99.2` for management instead of eBGP link IP.

---

## 15. FRR BGP output does not say Established

**Symptom:** Bootstrap script BGP check always fails even when BGP is up.  
**Root cause:** FRR shows uptime in the Up/Down column when session is up, not the word `Established`.  
**Fix:** Check for neighbor description present and not `Active` or `Idle` instead of looking for `Established`.

---

## 16. Ping output format differs Alpine vs Ubuntu

**Symptom:** Bootstrap ping check returns false negative on Alpine nodes.  
**Root cause:** Alpine ping: `N packets received`. Ubuntu ping: `N received`.  
**Fix:** Check for `" received"` and `"0 received" not in output`.

---

## 17. iptables NAT duplicates on repeated bootstrap runs

**Symptom:** Multiple duplicate MASQUERADE rules after running bootstrap twice.  
**Root cause:** Bootstrap adds rules without checking if they already exist.  
**Fix:** Flush before adding:
```python
run_config(conn, "iptables -F FORWARD")
run_config(conn, "iptables -t nat -F POSTROUTING")
```

---

## 18. FRR-R2 VMnet8 VM-to-VM traffic blocked

**Symptom:** Ubuntu cannot ping or SSH to FRR-R2 at `192.168.254.135` despite correct ARP.  
**Root cause:** VMware VMnet8 (NAT adapter) silently drops direct VM-to-VM traffic. The adapter is designed for VM-to-host and VM-to-internet only.  
**Fix:** Added loopback `10.0.99.2/32` on FRR-R2 and static route on FRR-R1 (`ip route 10.0.99.2/32 10.0.12.2`). Ubuntu reaches FRR-R2 via FRR-R1 routing. Added return route on FRR-R2 (`ip route add 192.168.66.0/24 via 10.0.12.1`).

---

## 19. FRR-R2 MASQUERADE too broad

**Symptom:** Ubuntu cannot reach FRR-R2 even after loopback fix — ICMP replies were being masqueraded.  
**Root cause:** MASQUERADE rule applied to all outbound traffic on eth0, including management replies.  
**Fix:** Scoped MASQUERADE to lab traffic only:
```bash
iptables -t nat -A POSTROUTING -s 10.0.0.0/8 -o eth0 -j MASQUERADE
```

---

## 20. Nornir KeyError: netmiko on credential injection

**Symptom:** `KeyError: 'netmiko'` when injecting credentials in `engine.py`.  
**Root cause:** Hosts without explicit `connection_options` in YAML have an empty dict — the key `netmiko` does not exist yet.  
**Fix:** Guard in `_inject_credentials` creates the `ConnectionOptions` object if missing before writing into it.

---

## 21. Nornir groups.yaml device_type conflict

**Symptom:** `ValueError: Unsupported device_type` for ASA despite correct config.  
**Root cause:** Setting both `platform` in groups.yaml and `device_type` in extras caused Netmiko to receive conflicting values.  
**Fix:** Removed `device_type` from all group extras. Nornir resolves device type from `platform` field automatically.

---

## 22. Compliance results showing stale data in dashboard

**Symptom:** Dashboard shows old FAIL results even after device is fixed.  
**Root cause:** Compliance panel reads from PostgreSQL — it shows last recorded result, not live state.  
**Fix:** Click **Run Compliance Now** in dashboard to insert fresh results, then **Refresh Now** to display them.

---

## 23. Streamlit device panel timeout

**Symptom:** `HTTPConnectionPool read timed out` on device status panel.  
**Root cause:** `/devices` endpoint SSHs into all devices live on every request, taking 20-30 seconds — exceeded the default 10 second timeout.  
**Fix:** Increased fetch timeout to 60 seconds for device endpoint. Added `@st.cache_data(ttl=60)` to cache device status for 60 seconds between requests.

---

## 24. Old compliance records polluting dashboard

**Symptom:** Dashboard showing `login_banner FAIL` results after policy was removed.  
**Root cause:** Old records from earlier compliance runs remained in PostgreSQL.  
**Fix:**
```bash
sudo docker exec -it netops_postgres psql -U netops -d netops_hub -c "DELETE FROM compliance_results WHERE policy = 'login_banner';"
```
