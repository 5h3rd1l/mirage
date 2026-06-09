# Mirage VPN — Release Notes
### Version 2.0.0 · Windows 11 x64 · 9 June 2026

---

## Download

| File | Size | SHA-256 |
|---|---|---|
| `Mirage.exe` | 43 MB | `04d11cb57cca399688122f3cbea0e1dae09c3b40f9acf4e08dbe83f9a3f445f7` |

---

## Features

- **AES-256-GCM encrypted tunnel** — all traffic encrypted per-packet with a random 12-byte nonce
- **Full-tunnel routing** — 0.0.0.0/1 + 128.0.0.0/1 split ensures all IPv4 traffic routes through the VPN
- **IP masking** — public IP changes to EC2 Stockholm (13.63.54.237) on connect
- **Wintun L3 adapter** — kernel-level virtual NIC via `wintun.dll` (bundled, no separate install)
- **Kill switch** — blocks all outbound traffic if VPN drops; restored automatically on exit via Windows Task Scheduler
- **Tor high-anonymity mode** — transparent proxy through Tor network (server-side TransPort 9040)
- **Email OTP verification** — account creation requires email confirmation via 6-digit code (10-min expiry)
- **Brute-force protection** — 5 failed logins triggers 15-minute account lockout
- **Real-time bandwidth graph** — 60-sample rolling upload/download chart
- **Interactive radar map** — animated jet transition between real location and VPN server on connect
- **Connection dashboard** — full session history, per-session data totals, CSV export
- **DNS leak protection** — sets 8.8.8.8 / 1.1.1.1 on all active adapters on connect, restores on disconnect
- **IPv6 leak prevention** — disables IPv6 binding on physical adapters while connected

---

## Requirements

- Windows 10/11 x64
- Administrator privileges (UAC prompt shown on launch)
- Ports 5000/TCP and 5001/UDP outbound to 13.63.54.237

---

## Installation

No installer needed. Run `Mirage.exe` directly. UAC will prompt for elevation automatically.

---

## Known Limitations

- Single server location (Stockholm, Sweden)
- Windows only — no macOS/Linux client in this release
- Tor mode adds latency (~200–500ms additional)
