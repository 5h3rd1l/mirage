import os
import sys
import socket
import threading
import json
import time
import subprocess
import ctypes
import ctypes.wintypes

# ── CONFIG ──────────────────────────────────────────
SERVER_IP  = "13.63.54.237"
AUTH_PORT  = 5000
TUN_PORT   = 5001
KEY        = bytes.fromhex("692a9f99c6b9f3dbe99442babfc884ac0fc23c0e006cc47518206847cc145089")
CLIENT_IP  = "10.8.0.2"
SERVER_VPN = "10.8.0.1"
DNS_SERVER = "8.8.8.8"
ADAPTER_NAME = "Mirage"
# ────────────────────────────────────────────────────

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def encrypt(data):
    nonce = os.urandom(12)
    return nonce + AESGCM(KEY).encrypt(nonce, data, None)

def decrypt(data):
    return AESGCM(KEY).decrypt(data[:12], data[12:], None)


# ── WINTUN (Lazy Loaded) ────────────────────────────
wintun = None

def _load_wintun():
    """Load wintun.dll lazily only when needed"""
    global wintun
    if wintun is not None:
        return wintun
    
    try:
        # Try to load from system PATH first
        wintun = ctypes.WinDLL("wintun.dll")
    except OSError:
        try:
            # Try local directory
            wintun = ctypes.WinDLL(os.path.join(os.path.dirname(__file__), "assets", "bin", "wintun.dll"))
        except OSError:
            raise RuntimeError("wintun.dll not found. Install WinTun driver from https://www.wintun.net/")
    
    # Setup function signatures
    wintun.WintunCreateAdapter.restype  = ctypes.c_void_p
    wintun.WintunCreateAdapter.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_void_p]

    wintun.WintunCloseAdapter.restype  = None
    wintun.WintunCloseAdapter.argtypes = [ctypes.c_void_p]

    wintun.WintunStartSession.restype  = ctypes.c_void_p
    wintun.WintunStartSession.argtypes = [ctypes.c_void_p, ctypes.c_ulong]

    wintun.WintunEndSession.restype  = None
    wintun.WintunEndSession.argtypes = [ctypes.c_void_p]

    wintun.WintunAllocateSendPacket.restype  = ctypes.c_void_p
    wintun.WintunAllocateSendPacket.argtypes = [ctypes.c_void_p, ctypes.c_ulong]

    wintun.WintunSendPacket.restype  = None
    wintun.WintunSendPacket.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

    wintun.WintunReceivePacket.restype  = ctypes.c_void_p
    wintun.WintunReceivePacket.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]

    wintun.WintunReleaseReceivePacket.restype  = None
    wintun.WintunReleaseReceivePacket.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

    wintun.WintunGetReadWaitEvent.restype  = ctypes.c_void_p
    wintun.WintunGetReadWaitEvent.argtypes = [ctypes.c_void_p]
    
    return wintun
# ────────────────────────────────────────────────────


def _run_ps(cmd):
    """Run a PowerShell command and return stdout."""
    r = subprocess.run(
        ['powershell', '-NoProfile', '-Command', cmd],
        capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW, text=True
    )
    return r.stdout.strip()


def _get_adapter_index(name=ADAPTER_NAME):
    """Get interface index by adapter name. Retries for up to 8 seconds."""
    for attempt in range(16):
        idx = _run_ps(f'(Get-NetAdapter -Name "{name}" -ErrorAction SilentlyContinue).ifIndex')
        if idx and idx.isdigit():
            return idx
        time.sleep(0.5)
    return None


def _verify_ip_assigned(if_index, expected_ip):
    """Check if the expected IP is actually assigned to the interface."""
    result = _run_ps(
        f'(Get-NetIPAddress -InterfaceIndex {if_index} -AddressFamily IPv4 '
        f'-ErrorAction SilentlyContinue).IPAddress'
    )
    assigned_ips = [ip.strip() for ip in result.splitlines() if ip.strip()]
    return expected_ip in assigned_ips


def set_adapter_ip(ip, prefix_len=24):
    """Assign IP to the Mirage Wintun adapter strictly via PowerShell."""
    print(f"[*] Waiting for adapter '{ADAPTER_NAME}' to initialize...")
    time.sleep(2)

    if_index = _get_adapter_index()
    if not if_index:
        print(f"[-] Adapter '{ADAPTER_NAME}' not found.")
        return None

    print(f"[*] Adapter index: {if_index}")

    # 1. Global Ghost-IP Purge (Fix Error 5010)
    r = subprocess.run(
        ['powershell', '-NoProfile', '-Command', 
         f'Get-NetIPAddress -IPAddress {ip} -ErrorAction SilentlyContinue | Remove-NetIPAddress -Confirm:$false'],
        capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW, text=True
    )
    if r.stderr:
        print(f"[*] Ghost-IP Purge stderr: {r.stderr.strip()}")
    time.sleep(0.5)

    # 2. Local APIPA Purge
    r = subprocess.run(
        ['powershell', '-NoProfile', '-Command', 
         f'Get-NetIPAddress -InterfaceIndex {if_index} -AddressFamily IPv4 -ErrorAction SilentlyContinue | Remove-NetIPAddress -Confirm:$false'],
        capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW, text=True
    )
    if r.stderr:
        print(f"[*] APIPA Purge stderr: {r.stderr.strip()}")
    time.sleep(0.5)

    # Assign IP
    r = subprocess.run(
        ['powershell', '-NoProfile', '-Command', 
         f'New-NetIPAddress -InterfaceIndex {if_index} -IPAddress {ip} -PrefixLength {prefix_len} -PolicyStore ActiveStore'],
        capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW, text=True
    )
    if r.stderr:
        print(f"[*] New-NetIPAddress stderr: {r.stderr.strip()}")
    time.sleep(1.0)

    # Set DNS
    _run_ps(
        f'Set-DnsClientServerAddress -InterfaceIndex {if_index} '
        f'-ServerAddresses ("{DNS_SERVER}","1.1.1.1") -ErrorAction SilentlyContinue'
    )

    # Verify
    ips = _run_ps(
        f'(Get-NetIPAddress -InterfaceIndex {if_index} -AddressFamily IPv4 '
        f'-ErrorAction SilentlyContinue).IPAddress'
    )
    print(f"[*] Adapter IPs verify dump: {ips}")
    
    if ip in [x.strip() for x in ips.splitlines() if x.strip()]:
        print(f"[+] IP {ip} successfully verified on adapter!")
    else:
        print(f"[-] WARNING: IP {ip} missing. Verify dump shows: {ips}")

    return if_index


def get_default_gateway():
    """Get current default gateway IP."""
    result = subprocess.run(['route', 'print', '0.0.0.0'],
                            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW, text=True)
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] == '0.0.0.0' and parts[1] == '0.0.0.0':
            gw = parts[2]
            if gw != '0.0.0.0':
                return gw

    # Fallback via PowerShell
    gw = _run_ps(
        '(Get-NetRoute -DestinationPrefix "0.0.0.0/0" '
        '| Sort-Object RouteMetric | Select-Object -First 1).NextHop'
    )
    return gw if gw and gw != '0.0.0.0' else '192.168.1.1'


def set_routes(original_gw, if_index):
    """Route all traffic through the Wintun adapter using on-link routes."""
    print(f"[*] Setting routes (original_gw={original_gw}, if={if_index})...")

    # 1. Keep the EC2 server reachable via original gateway (prevents routing loop)
    subprocess.run(['route', 'add', SERVER_IP, 'mask', '255.255.255.255', original_gw, 'metric', '1'],
                   capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)

    # 2. Also keep DNS reachable directly (in case it routes through original GW)
    subprocess.run(['route', 'add', DNS_SERVER, 'mask', '255.255.255.255', original_gw, 'metric', '1'],
                   capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    subprocess.run(['route', 'add', '1.1.1.1', 'mask', '255.255.255.255', original_gw, 'metric', '1'],
                   capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)

    # 3. Add split-tunnel routes through Wintun adapter
    if if_index:
        subprocess.run(
            ['route', 'add', '0.0.0.0', 'mask', '128.0.0.0',
             SERVER_VPN, 'metric', '3', 'if', if_index],
            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
        )
        subprocess.run(
            ['route', 'add', '128.0.0.0', 'mask', '128.0.0.0',
             SERVER_VPN, 'metric', '3', 'if', if_index],
            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
        )
    else:
        subprocess.run(
            ['route', 'add', '0.0.0.0', 'mask', '128.0.0.0', SERVER_VPN, 'metric', '3'],
            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
        )
        subprocess.run(
            ['route', 'add', '128.0.0.0', 'mask', '128.0.0.0', SERVER_VPN, 'metric', '3'],
            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
        )

    print(f"[+] Routes set. All traffic -> Wintun -> EC2 -> Internet")


def restore_routes(original_gw):
    """Restore original routing table on disconnect."""
    print(f"[*] Restoring routes to gateway {original_gw}...")
    subprocess.run(['route', 'delete', '0.0.0.0', 'mask', '128.0.0.0'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    subprocess.run(['route', 'delete', '128.0.0.0', 'mask', '128.0.0.0'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    subprocess.run(['route', 'delete', SERVER_IP], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    subprocess.run(['route', 'delete', DNS_SERVER, 'mask', '255.255.255.255'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    subprocess.run(['route', 'delete', '1.1.1.1', 'mask', '255.255.255.255'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    print(f"[+] Routes restored")


class WintunClient:
    def __init__(self, token: str, tor_mode: bool = False):
        self.token       = token
        self.tor_mode    = tor_mode
        self.running     = False
        self.adapter     = None
        self.session     = None
        self.auth_conn   = None
        self.udp_sock    = None
        self.original_gw = None
        self.if_index    = None
        self.bytes_sent  = 0
        self.bytes_recv  = 0
        self.on_bandwidth = None  # callback(up_mbps, down_mbps)

    def connect(self):
        print("=" * 60)
        print("  Mirage VPN — Connecting (UDP L3 Relay)")
        print("=" * 60)

        # Load wintun DLL (lazy load)
        _load_wintun()

        # Step 1 — Get default gateway BEFORE anything changes
        self.original_gw = get_default_gateway()
        print(f"[*] Original gateway: {self.original_gw}")

        # Step 2 — TCP auth
        print(f"[*] Authenticating with {SERVER_IP}:{AUTH_PORT}...")
        self.auth_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.auth_conn.settimeout(10)
        self.auth_conn.connect((SERVER_IP, AUTH_PORT))

        auth_msg = json.dumps({
            "type": "auth",
            "token": self.token,
            "tor_mode": self.tor_mode
        }).encode()
        self.auth_conn.send(encrypt(auth_msg))
        resp = json.loads(decrypt(self.auth_conn.recv(4096)))

        if resp.get("status") != "ok":
            raise Exception(resp.get("message", "Auth failed"))

        print(f"[+] Authenticated — server says: {resp.get('message')}")

        # Step 3 — Create Wintun adapter
        print(f"[*] Creating Wintun adapter '{ADAPTER_NAME}'...")
        self.adapter = wintun.WintunCreateAdapter(ADAPTER_NAME, "Wintun", None)
        if not self.adapter:
            err = ctypes.get_last_error()
            raise Exception(f"WintunCreateAdapter failed: error {err}. Run as Administrator!")
        print(f"[+] Wintun adapter '{ADAPTER_NAME}' created")

        # Step 4 — Start session
        self.session = wintun.WintunStartSession(self.adapter, 0x400000)
        if not self.session:
            raise Exception("WintunStartSession failed")
        print(f"[+] Wintun session started")

        # Step 5 — Assign IP to adapter
        self.if_index = set_adapter_ip(CLIENT_IP)
        if not self.if_index:
            raise Exception("Failed to get adapter interface index")

        # Step 6 — Set routes (traffic → Wintun → server → internet)
        set_routes(self.original_gw, self.if_index)

        # Step 7 — UDP tunnel socket
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_sock.bind(('0.0.0.0', 0))
        self.udp_sock.settimeout(5)

        self.running = True
        self.auth_conn.settimeout(None)

        # Register our UDP address with the server
        print(f"[*] Registering UDP endpoint with server...")
        for i in range(3):
            hello = encrypt(json.dumps({"type": "hello"}).encode())
            self.udp_sock.sendto(hello, (SERVER_IP, TUN_PORT))
            time.sleep(0.3)
            # Try to receive hello_ack
            try:
                self.udp_sock.settimeout(1)
                data, _ = self.udp_sock.recvfrom(4096)
                ack = json.loads(decrypt(data))
                if ack.get("type") == "hello_ack" or ack.get("status") == "ok":
                    print(f"[+] Server acknowledged UDP registration")
                    break
            except (socket.timeout, Exception):
                if i < 2:
                    print(f"[*] Retrying UDP registration ({i+2}/3)...")
        else:
            print(f"[!] No UDP ack from server — continuing anyway")

        self.udp_sock.settimeout(5)

        # Start relay threads
        threading.Thread(target=self._tun_to_udp, daemon=True).start()
        threading.Thread(target=self._udp_to_tun, daemon=True).start()
        threading.Thread(target=self._keepalive,  daemon=True).start()
        threading.Thread(target=self._bw_loop, daemon=True).start()

        print("=" * 60)
        print("  [+] Mirage VPN CONNECTED!")
        print(f"  [+] Your IP should now appear as: {SERVER_IP}")
        print("=" * 60)
        return True

    def _tun_to_udp(self):
        """Read packets from Wintun -> encrypt -> send to server."""
        print("[*] tun->udp thread started")
        wait_event = wintun.WintunGetReadWaitEvent(self.session)
        while self.running:
            try:
                size = ctypes.c_ulong(0)
                packet_ptr = wintun.WintunReceivePacket(self.session, ctypes.byref(size))
                if packet_ptr:
                    raw = ctypes.string_at(packet_ptr, size.value)
                    wintun.WintunReleaseReceivePacket(self.session, packet_ptr)
                    try:
                        self.udp_sock.sendto(encrypt(raw), (SERVER_IP, TUN_PORT))
                        self.bytes_sent += len(raw)
                    except Exception as e:
                        if self.running:
                            print(f"[-] tun->udp send error: {e}")
                else:
                    ctypes.windll.kernel32.WaitForSingleObject(wait_event, 100)
            except Exception as e:
                time.sleep(0.01)

    def _udp_to_tun(self):
        """Receive packets from server -> decrypt -> write to Wintun."""
        print("[*] udp->tun thread started")
        while self.running:
            try:
                data, _ = self.udp_sock.recvfrom(65535)
                packet  = decrypt(data)

                # Skip control messages
                if len(packet) < 20:
                    continue
                version = (packet[0] >> 4) & 0xF
                if version != 4:
                    continue

                buf_ptr = wintun.WintunAllocateSendPacket(self.session, len(packet))
                if buf_ptr:
                    ctypes.memmove(buf_ptr, packet, len(packet))
                    wintun.WintunSendPacket(self.session, buf_ptr)
                    self.bytes_recv += len(packet)
            except socket.timeout:
                continue
            except Exception as e:
                time.sleep(0.01)

    def _keepalive(self):
        """Keep TCP auth connection alive to maintain session."""
        print("[*] keepalive thread started")
        while self.running:
            try:
                time.sleep(5)
                if not self.running:
                    break
                ping = encrypt(json.dumps({"type": "ping"}).encode())
                self.auth_conn.send(ping)
                self.auth_conn.settimeout(10)
                self.auth_conn.recv(4096)
            except Exception as e:
                if self.running:
                    print(f"[-] Keepalive lost: {e}")
                    self.running = False
                break

    def _bw_loop(self):
        """Report tunnel throughput once per second."""
        last_sent, last_recv = self.bytes_sent, self.bytes_recv
        while self.running:
            time.sleep(1)
            sent = self.bytes_sent
            recv = self.bytes_recv
            if self.on_bandwidth:
                up_mbps = (sent - last_sent) * 8 / 1_000_000
                down_mbps = (recv - last_recv) * 8 / 1_000_000
                try:
                    self.on_bandwidth(up_mbps, down_mbps)
                except Exception:
                    pass
            last_sent, last_recv = sent, recv

    def disconnect(self):
        print("[*] Disconnecting Mirage VPN...")
        self.running = False

        if self.udp_sock:
            try:
                self.udp_sock.close()
            except Exception:
                pass

        if self.session:
            try:
                wintun.WintunEndSession(self.session)
            except Exception:
                pass
            self.session = None

        if self.adapter:
            try:
                wintun.WintunCloseAdapter(self.adapter)
            except Exception:
                pass
            self.adapter = None

        if self.original_gw:
            restore_routes(self.original_gw)

        if self.auth_conn:
            try:
                self.auth_conn.close()
            except Exception:
                pass

        print("[+] Disconnected. Routes and adapter restored.")