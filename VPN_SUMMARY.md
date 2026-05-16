# Mirage VPN — Project Documentation

**Course:** Network Security  
**Team:** Team 4  
**Server:** AWS EC2 — Europe (Stockholm) `13.63.54.237`  
**Deadline:** June 5, 2026  

---

## Team Members

| # | Name | Module |
|---|------|--------|
| 1 | Awad Ahmed | Encrypted Tunnel & Server Infrastructure |
| 2 | Rubas Ali | Authentication System |
| 3 | Sohaib Shahzad | GUI & Kill Switch |
| 4 | Syed Hadi Ali | Traffic Logging & Live Dashboard |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| VPN Client GUI | Python + PyQt5 (Neumorphic / Glassmorphic theme) |
| VPN Tunnel | Wintun L3 adapter + encrypted UDP relay |
| Encryption | AES-256-GCM (`cryptography` library) |
| Auth API | Cloudflare Workers |
| Database | Supabase (PostgreSQL) |
| VPN Server | Python on AWS EC2 (Ubuntu 26.04) |
| Routing | System TUN interface (`/dev/net/tun`) + iptables NAT |
| High Anonymity | Tor Transparent Proxy (TransPort 9040 + DNSPort 5353) |
| Email | Resend |
| Error Tracking | Sentry |
| Packaging | cx_Freeze → `MirageVPN.exe` (UAC admin) |
| Version Control | GitHub (`5h3rd1l/mirage`) |

---

## Infrastructure

### AWS EC2
- **Region:** Europe (Stockholm) `eu-north-1`
- **Instance:** `t3.micro` (free tier)
- **OS:** Ubuntu 26.04 LTS
- **Elastic IP:** `13.63.54.237` (permanent)
- **Key Pair:** `vpn-key.pem`

### Open Ports (Security Group)
| Protocol | Port | Purpose |
|----------|------|---------|
| TCP | 22 | SSH |
| TCP | 5000 | VPN Auth + Keepalive tunnel |
| UDP | 5001 | L3 TUN packet relay |
| TCP | 1080 | SOCKS5 proxy (legacy) |

### Supabase
- **Project URL:** `https://sjbymnijaogswmysubfu.supabase.co`
- **Region:** Northeast Asia (Seoul)

### Cloudflare Workers
- **Worker URL:** `https://mirage.rubasali-paf.workers.dev`
- **Endpoints:**
  - `POST /register` — Create account
  - `POST /login` — Authenticate, returns session token
  - `POST /verify` — Validate session token (used by server)

---

## Database Schema

### `users`
```sql
id            UUID PRIMARY KEY
username      TEXT UNIQUE NOT NULL
email         TEXT UNIQUE NOT NULL
password_hash TEXT NOT NULL
is_verified   BOOLEAN DEFAULT FALSE
failed_attempts INT DEFAULT 0
locked_until  TIMESTAMP
created_at    TIMESTAMP DEFAULT NOW()
```

### `sessions`
```sql
id         UUID PRIMARY KEY
user_id    UUID REFERENCES users(id)
token      TEXT UNIQUE NOT NULL
ip_address TEXT
created_at TIMESTAMP DEFAULT NOW()
expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '24 hours'
is_active  BOOLEAN DEFAULT TRUE
```

### `connection_logs`
```sql
id             UUID PRIMARY KEY
user_id        UUID REFERENCES users(id)
event          TEXT NOT NULL  -- 'connect' | 'disconnect'
ip_address     TEXT
bytes_sent     BIGINT DEFAULT 0
bytes_received BIGINT DEFAULT 0
timestamp      TIMESTAMP DEFAULT NOW()
```

---

## Encryption

- **Algorithm:** AES-256-GCM
- **Key:** 256-bit symmetric key (hardcoded for demo)
- **Nonce:** 12 random bytes prepended to every packet
- **Why GCM:** Provides both encryption AND integrity verification

### Packet Structure
```
[ 12 bytes nonce ][ encrypted ciphertext ]
```

### Key
```
692a9f99c6b9f3dbe99442babfc884ac0fc23c0e006cc47518206847cc145089
```

---

## Authentication Flow

```
Client                    Cloudflare Workers         Supabase
──────                    ──────────────────         ────────
POST /register ─────────► hash password (PBKDF2)
                          store user ────────────────► users table
                          return 200 ◄────────────────

POST /login ────────────► verify password hash
                          create session token ───────► sessions table
                          return token ◄──────────────

VPN connect ────────────► POST /verify (token)
                          check sessions table ───────► valid?
                          return {valid, user_id} ◄───
```

**Security features:**
- PBKDF2 password hashing (100,000 iterations, SHA-256)
- Session tokens expire after 24 hours
- Account lockout after 5 failed login attempts (15 minute lockout)
- Token travels only once (at login); subsequent requests use session token

---

## VPN Tunnel Architecture

### Current Implementation — L3 UDP Relay

The VPN uses a **Layer-3 encrypted UDP tunnel** with a Wintun virtual network adapter on the client side and a Linux TUN interface on the server side.

```
┌──────────────────────────────────────────────────────────────┐
│  CLIENT (Windows)                                            │
│                                                              │
│  Browser/App ──► Wintun adapter (10.8.0.2) ──► wintun_client│
│                                      │                       │
│                        ┌─────────────┘                       │
│                        │ (encrypted UDP packets)             │
│                        ▼                                     │
│                   UDP ──► 13.63.54.237:5001                  │
└──────────────────────────────────────────────────────────────┘
                         │
                    (AES-256-GCM)
                         │
┌──────────────────────────────────────────────────────────────┐
│  SERVER (EC2 Ubuntu)                                         │
│                                                              │
│  UDP :5001 ──► server.py ──► TUN interface (tun0, 10.8.0.1) │
│                                      │                       │
│                        ┌─────────────┘                       │
│                        │ (iptables MASQUERADE)                │
│                        ▼                                     │
│                   ens5 (NAT) ──► Internet                     │
└──────────────────────────────────────────────────────────────┘
```

### Normal Mode
```
Windows Client ──AES-256──► EC2 Stockholm ──NAT──────► Internet
                              (13.63.54.237)
```

### High Anonymity Mode (Tor)
```
Windows Client ──AES-256──► EC2 Stockholm ──Tor──────► Internet
                              (13.63.54.237)   (3 hops)
```

When Tor mode is active, the server applies iptables rules to redirect client traffic through Tor's TransPort (9040) and DNSPort (5353).

### Connection Sequence

1. **TCP Auth** — Client connects to `SERVER:5000`, sends encrypted auth token
2. **Server Verifies** — Token checked via Cloudflare Workers `/verify` endpoint
3. **Wintun Adapter Created** — Client creates virtual NIC `Mirage` via `wintun.dll`
4. **IP Assignment** — Client assigns `10.8.0.2/24` to adapter via PowerShell
5. **Route Table Updated** — Default route points through Wintun (split 0/1 trick)
6. **UDP Registration** — Client sends `hello` packets to `SERVER:5001`
7. **Relay Threads Start** — Bidirectional encrypted relay: `tun→udp` and `udp→tun`
8. **Keepalive** — TCP keepalive pings every 5s maintain the session

---

## Server Setup (EC2)

### SSH Access
```bash
ssh -i ~/vpn-key.pem ubuntu@13.63.54.237
```

### Installed Packages
```bash
sudo apt install python3 python3-pip tor screen -y
pip3 install cryptography --break-system-packages
```

### IP Forwarding + NAT (set automatically by server.py)
```bash
sysctl -w net.ipv4.ip_forward=1
iptables -t nat -A POSTROUTING -s 10.8.0.0/24 ! -d 10.8.0.0/24 -j MASQUERADE
iptables -A FORWARD -i tun0 -j ACCEPT
iptables -A FORWARD -o tun0 -j ACCEPT
```

### Deployment
```bash
scp -i ~/vpn-key.pem server.py ubuntu@13.63.54.237:~/vpn-server/
ssh -i ~/vpn-key.pem ubuntu@13.63.54.237 "bash ~/vpn-server/deploy_server.sh"
```

### Running Server
```bash
screen -S mirage
sudo python3 ~/vpn-server/server.py
# Detach: CTRL+A then D
# Reattach: screen -r mirage
```

### Server Ports
- Port `5000` (TCP) — VPN auth + keepalive tunnel
- Port `5001` (UDP) — L3 TUN packet relay

### Server Components
- **TUN interface** — Linux TUN (`/dev/net/tun`) named `tun0` at `10.8.0.1/24`
- **UDP relay** — Bidirectional `tun↔client` encrypted packet relay
- **Auth handler** — TCP socket authenticates clients, manages sessions
- **Tor daemon** — Isolated instance with custom `torrc`, started at server boot
- **Tor routing** — iptables `PREROUTING REDIRECT` rules applied per-client

---

## Client Setup (Windows)

### Prerequisites
- Python 3.x
- `pip install PyQt5 cryptography pywin32`
- `wintun.dll` in client folder (from wintun.net, amd64)
- **Must run as Administrator** (Wintun adapter + route changes require elevation)

### Running
```powershell
# Run as Administrator
cd D:\mirage\client
python mirage_gui.py
```

### Route Configuration (automated by wintun_client.py)
```powershell
# Preserve server connectivity via original gateway
route add 13.63.54.237 mask 255.255.255.255 <original_gw> metric 1

# Split-tunnel routes through Wintun adapter
route add 0.0.0.0 mask 128.0.0.0 10.8.0.1 metric 3 if <wintun_ifIndex>
route add 128.0.0.0 mask 128.0.0.0 10.8.0.1 metric 3 if <wintun_ifIndex>
```

### Packaging (cx_Freeze)
```powershell
python setup.py build
# Output: MirageVPN.exe in build/ directory
```

---

## Kill Switch

Blocks all internet traffic if VPN drops unexpectedly.

**Activate:**
```powershell
netsh advfirewall set allprofiles firewallpolicy blockinbound,blockoutbound
```

**Deactivate:**
```powershell
netsh advfirewall set allprofiles firewallpolicy blockinbound,allowoutbound
```

**Safety nets implemented:**
1. `closeEvent` — restores firewall when X button clicked
2. `atexit` — restores on normal Python exit
3. `_restore_firewall_on_startup` — restores on next app launch (crash recovery)
4. Windows Task Scheduler task `MirageFirewallRestore` — restores on system startup
5. `SIGTERM` / `SIGHUP` signal handlers — restore on signal-based termination

---

## GUI Design

The client uses a **Neumorphic / Glassmorphic** aesthetic with a custom frameless window.

### Screens
| Screen | Description |
|--------|-------------|
| **LoginScreen** | Split-panel: hero branding (left) + login/register/verify forms (right) |
| **VerifyEmailScreen** | Enter 6-digit OTP sent via Resend; resend code or go back to login |
| **MainScreen** | Map radar widget, connect button with pulse glow, status bar, bottom dock |
| **DashboardScreen** | Stats cards, connection history table, CSV export |

### Key UI Features
- Frameless window with custom title bar (drag-to-move)
- Gaussian-blur gradient background with soft color blobs
- Dot-matrix world map with animated radar pulse rings
- Toast notification system (info / success / error)
- Connect button with idle pulse animation + glow effect
- Password visibility toggle on auth fields
- Mode toggle buttons (Sign In / Register)
- Bottom dock with Kill Switch and High Anonymity toggles

---

## Dashboard

Accessible via 📊 button in main screen.

**Shows:**
- Total sessions count
- Total data uploaded / downloaded
- Full connection history table (event, IP, bytes, timestamp, user ID)
- Export to CSV button
- Refresh button

Data fetched directly from Supabase `connection_logs` table (service role key).

---

## Features

| Feature | Status |
|---------|--------|
| User registration + login | ✅ |
| AES-256-GCM encrypted tunnel | ✅ |
| Token-based authentication | ✅ |
| Session management (Supabase) | ✅ |
| Kill Switch (5 safety nets) | ✅ |
| High Anonymity (Tor) mode | ✅ |
| Traffic logging to Supabase | ✅ |
| Live dashboard with stats | ✅ |
| CSV export | ✅ |
| IP / location display | ✅ |
| Account lockout (brute force) | ✅ |
| Wintun L3 TUN adapter | ✅ |
| UDP encrypted packet relay | ✅ |
| IP change after VPN connect | ✅ (NAT masquerade) |
| Full traffic routing through VPN | ✅ (split 0/1 routes) |
| cx_Freeze packaging (.exe) | ✅ |
| Tor transparent proxy on server | ✅ |
| Custom frameless GUI | ✅ |
| Email OTP verification (Resend) | ⚠️ Implemented, email delivery under investigation |
| Bot/spam account prevention | ⚠️ Logic complete, blocked on email delivery |

---

## Project Structure

```
mirage/
├── client/
│   ├── mirage_gui.py          # Main GUI application (PyQt5)
│   ├── wintun_client.py       # Wintun adapter + UDP L3 tunnel
│   ├── setup.py               # cx_Freeze packaging config
│   ├── Mirage VPN.spec        # PyInstaller spec (alt packaging)
│   ├── wintun.dll             # Wintun driver DLL (amd64)
│   ├── tun2socks.zip          # Legacy tun2socks archive
│   ├── build/                 # cx_Freeze build output
│   └── dist/                  # Distribution output
├── server/
│   ├── server.py              # VPN server (auth + TUN + UDP relay + Tor)
│   └── deploy_server.sh       # EC2 deployment script
├── workers/
│   └── vpn-auth/              # Cloudflare Workers auth API
│       ├── src/index.js        # API routes (register/login/verify/verify-email/resend-code)
│       ├── wrangler.toml       # Cloudflare config + env vars
│       └── package.json
├── VPN_SUMMARY.md             # This file
└── .gitignore
```

---

## Wireshark Demo Plan

1. Open Wireshark → select WiFi interface
2. Filter: `ip.addr == 13.63.54.237`
3. Connect Mirage VPN
4. Browse the web / send test data
5. Show captured packets — all encrypted (AES-256-GCM, unreadable)
6. Compare with unencrypted HTTP traffic to show the difference
7. Show IP change: `ip-api.com` returns `13.63.54.237` instead of real IP

---

## Important Credentials & Keys

> ⚠️ **For internal team use only. Do not share publicly.**

| Item | Value |
|------|-------|
| EC2 Public IP | `13.63.54.237` |
| EC2 Private IP | `172.31.33.197` |
| VPN AES Key | `692a9f99c6b9f3dbe99442babfc884ac0fc23c0e006cc47518206847cc145089` |
| Supabase URL | `https://sjbymnijaogswmysubfu.supabase.co` |
| Cloudflare Worker | `https://mirage.rubasali-paf.workers.dev` |
| Client VPN IP | `10.8.0.2` |
| Server VPN IP | `10.8.0.1` |
| VPN Subnet | `10.8.0.0/24` |
| Tor TransPort | `9040` |
| Tor DNSPort | `5353` |
| Email Domain | `mirage.ninja` (verified on Resend via DKIM/SPF/DMARC) |
| Resend Sender | `noreply@mirage.ninja` |

---

## Known Issues & Current Status

### ⚠️ Email OTP Delivery (In Progress)
- **What's done:** Full OTP flow implemented end-to-end — `POST /register` generates a 6-digit code, saves it to `verification_codes` table in Supabase (10-minute expiry), and sends via Resend API. `POST /verify-email` validates the code and sets `is_verified = true`. `POST /login` blocks unverified accounts. `POST /resend-code` replaces old codes.
- **What's broken:** Emails are not arriving in the test inbox (`rubasali.paf@gmail.com`). Resend API is responding (no errors returned from `/resend-code`), but no email is received — checked spam/junk.
- **Domain:** `mirage.ninja` was purchased on name.com. All 4 DNS records (DKIM TXT, MX, SPF TXT, DMARC TXT) were added. Resend shows Domain Status as **Verified**.
- **RESEND_API_KEY** was uploaded as a Wrangler secret and the worker was deployed successfully.
- **Suspected causes:** Gmail may be filtering; Resend free-tier may have sending restrictions; or the `from` address format in the API call may need adjustment.
- **Next steps to try:** Test sending to a non-Gmail address; check Resend dashboard Logs tab for send attempts; confirm the `verification_codes` table was created in Supabase.

### ⚠️ Wintun IP Assignment Instability
- Occasionally the Wintun adapter gets an APIPA address (`169.254.x.x`) instead of `10.8.0.2`.
- Root cause: `netsh` IP assignment via PowerShell subprocess sometimes races with Windows adapter initialization.
- Workaround: Reconnect usually resolves it.

---

## References

- Stallings, W. — Cryptography and Network Security (7th Ed.)
- Python cryptography docs: https://cryptography.io
- WireGuard/Wintun: https://www.wintun.net
- Cloudflare Workers docs: https://developers.cloudflare.com/workers
- Supabase docs: https://supabase.com/docs
- AWS EC2 docs: https://docs.aws.amazon.com/ec2
- Tor Project: https://www.torproject.org

---

*Last updated: May 16, 2026*