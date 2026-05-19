# Mirage VPN

A secure, cross-platform VPN application featuring **AES-256-GCM encryption**, multi-mode routing, kill switch protection, and real-time traffic monitoring — available on **Windows** and **Android**.

---

## Features

| Feature | Description |
|---------|-------------|
| 🔐 AES-256-GCM Encryption | 256-bit key, 12-byte nonce per packet — encryption + integrity |
| 🛡️ Kill Switch | 5-layer firewall protection — blocks all traffic if VPN drops |
| 🧅 Tor High-Anonymity Mode | Routes traffic through Tor TransPort for maximum anonymity |
| 📊 Live Dashboard | Real-time stats, session history, upload/download tracking |
| 📧 Email OTP Verification | Secure account creation with 6-digit OTP via Resend |
| 🔒 Brute-Force Protection | Account lockout after 5 failed attempts (15-minute cooldown) |
| 📱 Cross-Platform | Windows (.exe) + Android (.apk) — same encryption protocol |
| 📤 CSV Export | Export connection history with duration calculations |
| 🌍 IP Masking | Full traffic routing through EC2 Stockholm server |

---

## Downloads

Head to the [Releases](https://github.com/5h3rd1l/mirage/releases) page to download:

- **`MirageVPN.exe`** — Windows standalone client (no Python required)
- **`MirageVPN.apk`** — Android client (Android 8.0+)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Windows GUI | Python + PyQt5 (Glassmorphic / Neumorphic theme) |
| Android App | Kotlin + Material Design 3 |
| VPN Tunnel (Windows) | Wintun L3 adapter + encrypted UDP relay |
| VPN Tunnel (Android) | Android VpnService API |
| Encryption | AES-256-GCM |
| Auth API | Cloudflare Workers |
| Database | Supabase (PostgreSQL) |
| VPN Server | Python on AWS EC2 (Ubuntu, eu-north-1) |
| Routing | TUN interface + iptables NAT |
| High Anonymity | Tor Transparent Proxy (TransPort 9040) |
| Email | Resend (DKIM/SPF/DMARC verified) |
| Error Tracking | Sentry |
| Packaging | PyInstaller → single `.exe` |

---

## Architecture

### VPN Tunnel

```
┌─────────────────────────────────────────────┐
│  CLIENT (Windows)                           │
│  Browser/App → Wintun (10.8.0.2) → UDP ───►│
└─────────────────────────────────────────────┘
                    │ AES-256-GCM
┌─────────────────────────────────────────────┐
│  SERVER (EC2 eu-north-1)                    │
│  UDP :5001 → server.py → tun0 (10.8.0.1)   │
│                        → iptables NAT       │
│                        → Internet           │
└─────────────────────────────────────────────┘
```

### Routing Modes

**Normal Mode:**
```
Client ──AES-256──► EC2 Stockholm ──NAT──► Internet
```

**High Anonymity (Tor) Mode:**
```
Client ──AES-256──► EC2 Stockholm ──Tor (3 hops)──► Internet
```

---

## Connection Flow

1. **TCP Auth** — Client authenticates via Cloudflare Workers `/verify`
2. **Wintun Adapter** — Virtual NIC `Mirage` created at `10.8.0.2/24`
3. **Route Update** — Default route redirected through Wintun (split 0/1 trick)
4. **UDP Registration** — Client registers with server at `:5001`
5. **Relay Start** — Bidirectional encrypted relay: `tun↔udp`
6. **Keepalive** — TCP ping every 5s maintains session

---

## Windows — Quick Start

### Option A: Executable (Recommended)

1. Download `MirageVPN.exe` from [Releases](https://github.com/5h3rd1l/mirage/releases)
2. Double-click — UAC prompt appears (admin required for Wintun)
3. Register or login
4. Click **Connect**

> **Note:** Place `wintun.dll` (amd64) in the same folder if not bundled. Download from [wintun.net](https://www.wintun.net).

### Option B: From Source

```powershell
# Install dependencies
pip install PyQt5 cryptography pywin32

# Run as Administrator
cd client
python mirage_gui.py
```

---

## Android — Quick Start

1. Download `MirageVPN.apk` from [Releases](https://github.com/5h3rd1l/mirage/releases)
2. Transfer to Android device → tap to install
3. Allow installation from unknown sources if prompted
4. Launch app → Register/Login → Tap **Connect** → Grant VPN permission

> Minimum: Android 8.0 (API 26). No root required.

---

## Kill Switch

Blocks all internet traffic if the VPN disconnects unexpectedly.

| Safety Net | Trigger |
|------------|---------|
| `closeEvent` | App window closed (X button) |
| `atexit` | Normal Python exit |
| Startup restore | Next app launch (crash recovery) |
| Task Scheduler | System startup (`MirageFirewallRestore`) |
| Signal handlers | `SIGTERM` / `SIGHUP` |

---

## Dashboard

Access via the 📊 button on the main screen.

- **Stat Cards** — Total sessions, upload/download bytes, active sessions
- **Session Bar Chart** — Visual connection activity timeline
- **Connection History** — Event, IP, bytes sent/received, duration, timestamp
- **Filter Views** — ALL / CONNECT / DISCONNECT
- **CSV Export** — Download filtered history with duration calculations

---

## GUI

Custom frameless window with **Glassmorphic / Neumorphic** design.

| Screen | Description |
|--------|-------------|
| **Login** | Split-panel: branding + login/register/verify forms |
| **Verify Email** | 6-digit OTP input with resend support |
| **Main** | Radar map widget, connect button with pulse animation |
| **Dashboard** | Stats, charts, connection logs, CSV export |

---

## Project Structure

```
mirage/
├── client/
│   ├── mirage_gui.py        # Windows GUI (PyQt5)
│   └── wintun_client.py     # Wintun adapter + UDP L3 tunnel
├── server/
│   ├── server.py            # VPN server (auth + TUN + relay + Tor)
│   └── deploy_server.sh     # EC2 deployment script
├── workers/
│   └── vpn-auth/            # Cloudflare Workers auth API
│       ├── src/index.js     # Routes: register/login/verify/verify-email
│       ├── wrangler.toml    # Cloudflare config
│       └── package.json
└── requirements.txt         # Python dependencies
```

---

## Authentication

- **Hashing:** PBKDF2-SHA256 (100,000 iterations)
- **Sessions:** Token-based, expire after 24 hours
- **Lockout:** 5 failed attempts → 15-minute lockout
- **OTP:** 6-digit codes, 10-minute expiry, sent via Resend

### API Endpoints (Cloudflare Workers)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register` | Create account |
| POST | `/login` | Authenticate, returns session token |
| POST | `/verify` | Validate session token |
| POST | `/verify-email` | Submit OTP code |
| POST | `/resend-code` | Resend OTP |

---

## Server Setup (EC2)

```bash
# SSH
ssh -i ~/vpn-key.pem ubuntu@<server-ip>

# Install dependencies
sudo apt install python3 python3-pip tor screen -y
pip3 install cryptography --break-system-packages

# Run
screen -S mirage
sudo python3 ~/vpn-server/server.py
# Detach: CTRL+A then D
```

### Required Open Ports

| Protocol | Port | Purpose |
|----------|------|---------|
| TCP | 22 | SSH |
| TCP | 5000 | VPN auth + keepalive |
| UDP | 5001 | L3 TUN packet relay |

---

## Building from Source

### Windows Executable

```powershell
python -m PyInstaller --onefile --windowed --name MirageVPN \
  --add-data "client/wintun_client.py;." \
  --hidden-import=PyQt5.QtCore \
  --hidden-import=PyQt5.QtGui \
  --hidden-import=PyQt5.QtWidgets \
  --hidden-import=cryptography \
  --distpath "." --workpath "build_temp" \
  client/mirage_gui.py
```

Or run `rebuild.bat` for one-click automated build.

### Android APK

```bash
cd android/MirageVPN
./gradlew assembleRelease
# Output: app/build/outputs/apk/release/app-release.apk
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.
