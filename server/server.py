import socket
import threading
import os
import urllib.request
import json
import struct
import subprocess
import fcntl
import time
import tempfile
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ── CONFIG ──────────────────────────────────────────
HOST         = '0.0.0.0'
AUTH_PORT    = 5000
TUN_PORT     = 5001
KEY          = bytes.fromhex("692a9f99c6b9f3dbe99442babfc884ac0fc23c0e006cc47518206847cc145089")
AUTH_API     = "https://mirage.rubasali-paf.workers.dev/verify"
SUPABASE_URL = "https://sjbymnijaogswmysubfu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNqYnltbmlqYW9nc3dteXN1YmZ1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3ODc1OTkyMSwiZXhwIjoyMDk0MzM1OTIxfQ.tkwFFX3l874OtpjyIY5V5go3rMZz6X-BqO_Nl0V73I8"

TUNSETIFF    = 0x400454ca
IFF_TUN      = 0x0001
IFF_NO_PI    = 0x1000

VPN_SUBNET    = "10.8.0.0"
SERVER_VPN_IP = "10.8.0.1"
CLIENT_VPN_IP = "10.8.0.2"

active_clients = {}
clients_lock   = threading.Lock()
# ────────────────────────────────────────────────────


# ── CRYPTO ──────────────────────────────────────────
def encrypt(data):
    nonce = os.urandom(12)
    return nonce + AESGCM(KEY).encrypt(nonce, data, None)

def decrypt(data):
    return AESGCM(KEY).decrypt(data[:12], data[12:], None)
# ────────────────────────────────────────────────────


# ── AUTH ─────────────────────────────────────────────
def verify_token_get_id(token):
    try:
        data = json.dumps({"token": token}).encode()
        req  = urllib.request.Request(
            AUTH_API, data=data,
            headers={"Content-Type": "application/json", "User-Agent": "MirageVPN/1.0"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as res:
            body = json.loads(res.read())
            if body.get("valid"):
                return body.get("user_id")
    except Exception as e:
        print(f"[-] Token verify error: {e}")
    return None
# ────────────────────────────────────────────────────


# ── LOGGING ──────────────────────────────────────────
def log_event(user_id, event, ip, bytes_sent=0, bytes_recv=0):
    try:
        if not user_id: return
        payload = json.dumps({
            "user_id": str(user_id), 
            "event": str(event),
            "ip_address": str(ip), 
            "bytes_sent": int(bytes_sent),
            "bytes_received": int(bytes_recv)
        }).encode()
        req = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/connection_logs", data=payload,
            headers={
                "Content-Type": "application/json",
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Prefer": "return=minimal"
            },
            method="POST"
        )
        urllib.request.urlopen(req, timeout=5)
        print(f"[+] Logged: {event} for {ip}")
    except Exception as e:
        print(f"[-] Log error: {e}")
# ────────────────────────────────────────────────────


# ── TUN INTERFACE ────────────────────────────────────
def create_tun():
    # Clean up any leftover tun0 from a previous run
    subprocess.run(['ip', 'link', 'delete', 'tun0'], stderr=subprocess.DEVNULL, check=False)

    tun = open('/dev/net/tun', 'r+b', buffering=0)
    ifr = struct.pack('16sH', b'tun0', IFF_TUN | IFF_NO_PI)
    fcntl.ioctl(tun, TUNSETIFF, ifr)

    # Flush any existing config on tun0
    subprocess.run(['ip', 'addr', 'flush', 'dev', 'tun0'], check=False)
    subprocess.run(['ip', 'addr', 'add', f'{SERVER_VPN_IP}/24', 'dev', 'tun0'], check=False)
    subprocess.run(['ip', 'link', 'set', 'dev', 'tun0', 'mtu', '1400', 'up'], check=True)

    # ── NAT: THIS IS WHAT MAKES IP CHANGE ──
    subprocess.run(['sysctl', '-w', 'net.ipv4.ip_forward=1'])

    # Flush old rules first to avoid duplicates
    subprocess.run(['iptables', '-t', 'nat', '-D', 'POSTROUTING',
                    '-s', '10.8.0.0/24', '!', '-d', '10.8.0.0/24',
                    '-j', 'MASQUERADE'], stderr=subprocess.DEVNULL, check=False)
    subprocess.run(['iptables', '-D', 'FORWARD', '-i', 'tun0', '-j', 'ACCEPT'], stderr=subprocess.DEVNULL, check=False)
    subprocess.run(['iptables', '-D', 'FORWARD', '-o', 'tun0', '-j', 'ACCEPT'], stderr=subprocess.DEVNULL, check=False)

    # Add fresh rules
    subprocess.run(['iptables', '-t', 'nat', '-A', 'POSTROUTING',
                    '-s', '10.8.0.0/24', '!', '-d', '10.8.0.0/24',
                    '-j', 'MASQUERADE'])
    subprocess.run(['iptables', '-A', 'FORWARD', '-i', 'tun0', '-j', 'ACCEPT'])
    subprocess.run(['iptables', '-A', 'FORWARD', '-o', 'tun0', '-j', 'ACCEPT'])
    
    # Clean up any old Tor redirects
    subprocess.run(['iptables', '-t', 'nat', '-D', 'PREROUTING', '-s', CLIENT_VPN_IP, '-p', 'tcp', '-j', 'REDIRECT', '--to-ports', '9040'], stderr=subprocess.DEVNULL, check=False)
    subprocess.run(['iptables', '-t', 'nat', '-D', 'PREROUTING', '-s', CLIENT_VPN_IP, '-p', 'udp', '--dport', '53', '-j', 'REDIRECT', '--to-ports', '5353'], stderr=subprocess.DEVNULL, check=False)
    # ────────────────────────────────────────

    print(f"[*] TUN interface created: tun0 ({SERVER_VPN_IP})")
    return tun

def start_tor_daemon():
    print("[*] Starting isolated Tor daemon for High Anonymity mode...")
    torrc = (
        "SocksPort 9051\n"
        "TransPort 0.0.0.0:9040\n"
        "DNSPort 0.0.0.0:5353\n"
        "AutomapHostsOnResolve 1\n"
        "VirtualAddrNetworkIPv4 10.192.0.0/10\n"
        "Log notice stdout\n"
        "DataDirectory /tmp/mirage_tor_data\n"
    )
    with open('/tmp/mirage_torrc', 'w') as f:
        f.write(torrc)
    
    subprocess.run(['mkdir', '-p', '/tmp/mirage_tor_data'])
    subprocess.run(['chown', '-R', 'ubuntu:ubuntu', '/tmp/mirage_tor_data', '/tmp/mirage_torrc'])
    
    # Launch Tor as 'ubuntu' user because running as root directly crashes it
    subprocess.Popen(['sudo', '-u', 'ubuntu', 'tor', '-f', '/tmp/mirage_torrc'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)  # wait for Tor to initialize

def enable_tor_routing():
    print("[+] Enabling Tor Transparent Proxy routes...")
    # Redirect all TCP traffic to TransPort
    subprocess.run(['iptables', '-t', 'nat', '-A', 'PREROUTING', '-s', CLIENT_VPN_IP, '-p', 'tcp', '-j', 'REDIRECT', '--to-ports', '9040'])
    # Redirect all UDP DNS traffic to DNSPort
    subprocess.run(['iptables', '-t', 'nat', '-A', 'PREROUTING', '-s', CLIENT_VPN_IP, '-p', 'udp', '--dport', '53', '-j', 'REDIRECT', '--to-ports', '5353'])

def disable_tor_routing():
    print("[-] Disabling Tor Transparent Proxy routes...")
    subprocess.run(['iptables', '-t', 'nat', '-D', 'PREROUTING', '-s', CLIENT_VPN_IP, '-p', 'tcp', '-j', 'REDIRECT', '--to-ports', '9040'], stderr=subprocess.DEVNULL, check=False)
    subprocess.run(['iptables', '-t', 'nat', '-D', 'PREROUTING', '-s', CLIENT_VPN_IP, '-p', 'udp', '--dport', '53', '-j', 'REDIRECT', '--to-ports', '5353'], stderr=subprocess.DEVNULL, check=False)


def is_ip_packet(data):
    """Check if data looks like a valid IPv4 packet."""
    if len(data) < 20:
        return False
    version = (data[0] >> 4) & 0xF
    return version == 4


def is_control_message(data):
    """Check if decrypted data is a JSON control message (hello/ping)."""
    try:
        msg = json.loads(data.decode('utf-8'))
        return isinstance(msg, dict), msg
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return False, None


# ── PACKET RELAY ─────────────────────────────────────
def tun_to_client(tun, udp_sock):
    """Read IP packets from TUN → encrypt → send to all active clients."""
    print("[*] tun→client relay started")
    while True:
        try:
            packet = tun.read(65535)
            if not packet or len(packet) < 20:
                continue

            if not is_ip_packet(packet):
                continue

            with clients_lock:
                clients = list(active_clients.values())
            for client in clients:
                try:
                    if client.get('addr'):
                        udp_sock.sendto(encrypt(packet), client['addr'])
                except Exception as e:
                    pass
        except Exception as e:
            time.sleep(0.1)


def client_to_tun(tun, udp_sock):
    """Receive encrypted packets from client → decrypt → write to TUN."""
    print("[*] client→tun relay started")
    while True:
        try:
            data, addr = udp_sock.recvfrom(65535)
            plaintext = decrypt(data)

            is_control, msg = is_control_message(plaintext)
            if is_control:
                msg_type = msg.get("type", "")
                if msg_type == "hello":
                    with clients_lock:
                        if CLIENT_VPN_IP not in active_clients:
                            active_clients[CLIENT_VPN_IP] = {"addr": addr, "user_id": None, "tor_mode": False}
                        else:
                            active_clients[CLIENT_VPN_IP]['addr'] = addr
                    try:
                        ack = encrypt(json.dumps({"status": "ok", "type": "hello_ack"}).encode())
                        udp_sock.sendto(ack, addr)
                    except Exception:
                        pass
                    continue
                elif msg_type == "ping":
                    try:
                        ack = encrypt(json.dumps({"status": "ok"}).encode())
                        udp_sock.sendto(ack, addr)
                    except Exception:
                        pass
                    continue
                else:
                    continue

            # Route packet to TUN if it's an IP packet
            if is_ip_packet(plaintext):
                with clients_lock:
                    if CLIENT_VPN_IP in active_clients:
                        active_clients[CLIENT_VPN_IP]['addr'] = addr
                tun.write(plaintext)

        except Exception as e:
            time.sleep(0.01)
# ────────────────────────────────────────────────────


# ── AUTH HANDLER ─────────────────────────────────────
def handle_auth(conn, addr):
    user_id = None
    token   = None
    bytes_sent = 0
    bytes_recv = 0
    try:
        data = conn.recv(4096)
        if not data:
            return
        bytes_recv += len(data)
        decrypted = decrypt(data)
        message   = json.loads(decrypted.decode())

        if message.get("type") != "auth":
            resp = encrypt(json.dumps({"status": "error", "message": "Send auth first"}).encode())
            conn.send(resp)
            return

        token   = message.get("token", "")
        tor     = message.get("tor_mode", False)
        print(f"[*] Verifying token for {addr}...")
        user_id = verify_token_get_id(token)

        if not user_id:
            resp = encrypt(json.dumps({"status": "error", "message": "Invalid token"}).encode())
            conn.send(resp)
            return

        print(f"[+] Auth success for {addr} — tunnel open (Tor: {tor})")

        if tor:
            enable_tor_routing()

        # Register client for UDP tunnel
        client_udp_addr = (addr[0], TUN_PORT)
        with clients_lock:
            active_clients[CLIENT_VPN_IP] = {
                "addr": client_udp_addr,
                "user_id": user_id,
                "tor_mode": tor
            }

        resp = encrypt(json.dumps({
            "status": "ok",
            "message": "Tunnel open",
            "client_ip": CLIENT_VPN_IP,
            "server_ip": SERVER_VPN_IP,
            "tun_port":  TUN_PORT
        }).encode())
        conn.send(resp)

        log_event(user_id, "connect", addr[0])

        # Keep alive — detect disconnect
        conn.settimeout(30)
        while True:
            try:
                data = conn.recv(4096)
                if not data:
                    break
                bytes_recv += len(data)
                msg = json.loads(decrypt(data))
                if msg.get("type") == "ping":
                    resp = encrypt(json.dumps({"status": "ok"}).encode())
                    conn.send(resp)
                    bytes_sent += len(resp)
            except socket.timeout:
                continue
            except Exception:
                break

    except Exception as e:
        print(f"[-] Auth error {addr}: {e}")
    finally:
        if tor:
            disable_tor_routing()
        conn.close()
        with clients_lock:
            active_clients.pop(CLIENT_VPN_IP, None)
        if user_id:
            log_event(user_id, "disconnect", addr[0], bytes_sent, bytes_recv)
        print(f"[-] {addr[0]} disconnected")
# ────────────────────────────────────────────────────


# ── SERVER ENTRY POINT ───────────────────────────────
def start_auth_server():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, AUTH_PORT))
    srv.listen(5)
    print(f"[*] Mirage VPN Server running on {HOST}:{AUTH_PORT}")
    while True:
        conn, addr = srv.accept()
        t = threading.Thread(target=handle_auth, args=(conn, addr), daemon=True)
        t.start()


if __name__ == "__main__":
    print("=" * 60)
    print("  Mirage L3 VPN Server (UDP Packet Relay + Tor)")
    print("=" * 60)

    start_tor_daemon()
    tun      = create_tun()
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind((HOST, TUN_PORT))
    print(f"[*] UDP tunnel listening on {HOST}:{TUN_PORT}")

    threading.Thread(target=tun_to_client,  args=(tun, udp_sock), daemon=True).start()
    threading.Thread(target=client_to_tun,  args=(tun, udp_sock), daemon=True).start()

    start_auth_server()
