import sys
import os
import atexit
import signal
import socket
import threading
import json
import time
import re
import math
import subprocess
import platform
import urllib.request
import urllib.error
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtCore import QMetaObject, Q_ARG, pyqtSlot, pyqtProperty

# -- CONFIG -----------------------------------------------------------------
VPN_SERVER_IP = "13.63.54.237"
VPN_SERVER_PORT = 5000
AES_KEY = bytes.fromhex("692a9f99c6b9f3dbe99442babfc884ac0fc23c0e006cc47518206847cc145089")
AUTH_API = "https://mirage.rubasali-paf.workers.dev"
# ---------------------------------------------------------------------------


# -- CRYPTO -----------------------------------------------------------------
def encrypt(data: bytes) -> bytes:
    nonce = os.urandom(12)
    return nonce + AESGCM(AES_KEY).encrypt(nonce, data, None)


def decrypt(data: bytes) -> bytes:
    return AESGCM(AES_KEY).decrypt(data[:12], data[12:], None)

_keep_alive = []


# -- STYLESHEET --------------------------------------------------------------
STYLESHEET = """
QWidget {
    background-color: transparent;
    color: #1C1C1E;
    font-family: 'Inter', 'Segoe UI Variable', 'Segoe UI', sans-serif;
    font-size: 15px;
}

QMainWindow {
    background-color: #F0F2F5;
}

#titleBar {
    background: transparent;
}

#trafficBtn {
    border: none;
    border-radius: 8px;
    min-width: 16px; max-width: 16px;
    min-height: 16px; max-height: 16px;
}

#card {
    background-color: #FFFFFF;
    border: none;
    border-radius: 32px;
}

#telemetryCard {
    background-color: #FFFFFF;
    border: none;
    border-radius: 24px;
}

#locationSelector {
    background-color: #FFFFFF;
    border: none;
    border-radius: 24px;
}

#sessionBar {
    background: transparent;
}

#statusBadge {
    border-radius: 14px;
    padding: 6px 18px;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 1px;
}

QLabel#labelTitle {
    color: #1C1C1E;
    font-size: 36px;
    font-weight: 900;
    letter-spacing: 4px;
}
QLabel#labelSubtitle {
    color: #8E8E93;
    font-size: 14px;
    letter-spacing: 2px;
}
QLabel#labelMetricValue {
    color: #1C1C1E;
    font-size: 28px;
    font-weight: 600;
}
QLabel#labelMetricUnit {
    color: #8E8E93;
    font-size: 14px;
    font-weight: 500;
}
QLabel#labelMetricCaption {
    color: #8E8E93;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 1px;
}
QLabel#labelFieldName {
    color: #8E8E93;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 2px;
}
QLabel#labelFieldValue {
    color: #1C1C1E;
    font-size: 15px;
    font-weight: 600;
    letter-spacing: 0.5px;
}
QLabel#labelStatus {
    color: #FF3B30;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 3px;
}
QLabel#labelStatusConnected {
    color: #00CC66;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 3px;
}
QLabel#labelStatusConnecting {
    color: #FFCC00;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 3px;
}
QLabel#labelError {
    color: #A63D35;
    font-size: 13px;
    background: rgba(255, 59, 48, 0.08);
    border: 1px solid rgba(255, 59, 48, 0.15);
    border-radius: 12px;
    padding: 10px 18px;
}
QLabel#labelSuccess {
    color: #00AA55;
    font-size: 13px;
    background: rgba(0, 204, 102, 0.08);
    border: 1px solid rgba(0, 204, 102, 0.15);
    border-radius: 12px;
    padding: 10px 18px;
}

QLineEdit {
    background-color: rgba(255, 255, 255, 0.60);
    border: 1px solid rgba(0, 0, 0, 0.06);
    border-radius: 16px;
    padding: 15px 20px;
    color: #1C1C1E;
    font-size: 15px;
    selection-background-color: rgba(0, 102, 255, 0.15);
}
QLineEdit:focus {
    border: 1px solid rgba(0, 102, 255, 0.35);
    background-color: rgba(255, 255, 255, 0.80);
}
QLineEdit::placeholder {
    color: #C7C7CC;
}

QPushButton#btnPrimary {
    background: #0066FF;
    color: white;
    border: none;
    border-radius: 16px;
    padding: 15px 28px;
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 2px;
}
QPushButton#btnPrimary:hover { background: #1A75FF; }
QPushButton#btnPrimary:pressed { background: #0052CC; }
QPushButton#btnPrimary:disabled {
    background: rgba(0, 0, 0, 0.06);
    color: #A0A0A0;
    border: 1px solid rgba(0, 0, 0, 0.04);
}

QPushButton#btnConnect {
    background: #0066FF;
    color: white;
    border: none;
    border-radius: 22px;
    padding: 14px 32px;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 1px;
}
QPushButton#btnConnect:hover { background: #1A75FF; }
QPushButton#btnConnect:pressed { background: #0052CC; }

QPushButton#btnCancel {
    background: #FF3B30;
    color: white;
    border: none;
    border-radius: 22px;
    padding: 14px 32px;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 1px;
}
QPushButton#btnCancel:hover { background: #FF5147; }

QPushButton#btnGhost {
    background: rgba(0, 0, 0, 0.04);
    color: #8E8E93;
    border: none;
    border-radius: 14px;
    padding: 12px 20px;
    font-size: 14px;
    font-weight: 600;
}
QPushButton#btnGhost:hover { background: rgba(0, 0, 0, 0.08); }

QPushButton#btnLogout {
    background: rgba(0, 0, 0, 0.04);
    color: #8E8E93;
    border: none;
    border-radius: 12px;
    padding: 6px 14px;
    font-size: 13px;
    font-weight: 700;
}
QPushButton#btnLogout:hover { background: rgba(0, 0, 0, 0.08); color: #FF3B30; }

QPushButton#btnDisconnect {
    background: #FF3B30;
    color: white;
    border: none;
    border-radius: 24px;
    min-width: 48px; max-width: 48px;
    min-height: 48px; max-height: 48px;
    font-size: 18px;
    font-weight: 700;
}
QPushButton#btnDisconnect:hover { background: #FF5147; }

QPushButton#modeBtn,
QPushButton#modeBtnActive {
    border-radius: 14px;
    padding: 11px 18px;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 2px;
}
QPushButton#modeBtn {
    background: rgba(0, 0, 0, 0.04);
    color: #8E8E93;
    border: none;
}
QPushButton#modeBtnActive {
    background: rgba(0, 102, 255, 0.08);
    color: #0066FF;
    border: none;
}

QCheckBox#toggle { spacing: 10px; color: #8E8E93; font-size: 14px; }
QCheckBox#toggle::indicator {
    width: 46px; height: 26px; border-radius: 14px;
    background-color: rgba(0, 0, 0, 0.08);
    border: none;
}
QCheckBox#toggle::indicator:checked {
    background-color: #0066FF;
}

QCheckBox#cbSave { spacing: 6px; color: #8E8E93; font-size: 13px; font-weight: 500; }
QCheckBox#cbSave::indicator {
    width: 14px; height: 14px; border-radius: 4px;
    background-color: rgba(255, 255, 255, 0.80);
    border: 1px solid rgba(0, 0, 0, 0.15);
}
QCheckBox#cbSave::indicator:checked {
    background-color: #0066FF;
    border: 1px solid #0066FF;
}
QCheckBox#cbSave::indicator:unchecked:hover {
    border: 1px solid rgba(0, 102, 255, 0.4);
}

QScrollBar:vertical {
    background: transparent; width: 5px; border-radius: 3px;
}
QScrollBar::handle:vertical {
    background: rgba(0, 0, 0, 0.10); border-radius: 3px;
}

#heroPanel {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(200, 220, 255, 0.40), stop:1 rgba(230, 210, 240, 0.30));
    border: none;
    border-radius: 24px;
}
QLabel#heroTitle {
    color: #1C1C1E;
    font-size: 34px;
    font-weight: 900;
    letter-spacing: 6px;
}
QLabel#heroSubtitle {
    color: #8E8E93;
    font-size: 15px;
    font-weight: 500;
}
QLabel#heroBadge {
    color: #636366;
    font-size: 13px;
    font-weight: 600;
    padding: 8px 18px;
    background: rgba(255, 255, 255, 0.50);
    border: none;
    border-radius: 12px;
}

#loginShell {
    background: rgba(255, 255, 255, 0.60);
    border: none;
    border-radius: 24px;
}

QPushButton#btnConnectActive {
    background: #00CC66;
    color: white;
    border: none;
    border-radius: 22px;
    padding: 14px 32px;
    font-size: 16px;
    font-weight: 700;
}

QPushButton#btnDanger {
    background: rgba(255, 59, 48, 0.08);
    color: #FF3B30;
    border: none;
    border-radius: 14px;
    padding: 12px 20px;
    font-size: 14px;
    font-weight: 600;
}
QPushButton#btnDanger:hover { background: rgba(255, 59, 48, 0.14); }
"""

# ---------------------------------------------------------------------------


class VPNWorker(QThread):
    """Background thread — manages VPN tunnel connection."""
    status_changed   = pyqtSignal(str)   # "connecting" | "connected" | "disconnected" | "error"
    bytes_updated    = pyqtSignal(int, int)  # sent, received
    bandwidth_update = pyqtSignal(float, float)  # KB/s sent, KB/s recv
    error_occurred   = pyqtSignal(str)

    def __init__(self, token: str, tor_mode: bool = False):
        super().__init__()
        self.token    = token
        self.tor_mode = tor_mode
        self.running  = False
        self.sock     = None
        self.bytes_sent = 0
        self.bytes_recv = 0

    def run(self):
        self.running = True
        self.status_changed.emit("connecting")
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10)
            self.sock.connect((VPN_SERVER_IP, VPN_SERVER_PORT))

            # Send auth token
            auth_msg = json.dumps({
                "type": "auth",
                "token": self.token,
                "tor_mode": self.tor_mode
            }).encode()
            payload = encrypt(auth_msg)
            self.sock.send(payload)
            self.bytes_sent += len(payload)

            # Wait for server response
            resp_data = self.sock.recv(4096)
            self.bytes_recv += len(resp_data)
            resp = json.loads(decrypt(resp_data))

            if resp.get("status") != "ok":
                self.status_changed.emit("error")
                self.error_occurred.emit(resp.get("message", "Auth failed"))
                return

            self.sock.settimeout(None)
            self.status_changed.emit("connected")

            def _bw_loop():
                last_sent, last_recv = 0, 0
                while self.running:
                    time.sleep(1)
                    s = self.bytes_sent
                    r = self.bytes_recv
                    self.bandwidth_update.emit((s - last_sent) / 1024, (r - last_recv) / 1024)
                    last_sent, last_recv = s, r

            threading.Thread(target=_bw_loop, daemon=True).start()

            # Keep-alive loop
            while self.running:
                time.sleep(5)
                if not self.running:
                    break
                try:
                    ping = encrypt(json.dumps({"type": "ping"}).encode())
                    self.sock.send(ping)
                    self.bytes_sent += len(ping)
                    pong = self.sock.recv(4096)
                    self.bytes_recv += len(pong)
                    self.bytes_updated.emit(self.bytes_sent, self.bytes_recv)
                except Exception:
                    if self.running:
                        self.status_changed.emit("error")
                        self.error_occurred.emit("Connection lost")
                    break

        except Exception as e:
            self.status_changed.emit("error")
            self.error_occurred.emit(str(e))
        finally:
            if self.sock:
                try:
                    self.sock.close()
                except Exception:
                    pass

    def stop(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass


class AuthWorker(QObject):
    """Background thread — handles login/register API calls."""
    auth_done = pyqtSignal(bool, str, str)  # success, token/error, username

    def __init__(self, action: str, username: str, password: str, email: str = ""):
        super().__init__()
        self.action   = action
        self.username = username
        self.password = password
        self.email    = email

    def start(self):
        threading.Thread(target=self.run, daemon=True).start()

    def run(self):
        try:
            if self.action == "login":
                payload = json.dumps({"username": self.username, "password": self.password}).encode()
                url = f"{AUTH_API}/login"
            else:
                payload = json.dumps({
                    "username": self.username,
                    "password": self.password,
                    "email": self.email
                }).encode()
                url = f"{AUTH_API}/register"

            req = urllib.request.Request(
                url, data=payload,
                headers={"Content-Type": "application/json", "User-Agent": "MirageVPN/1.0"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as res:
                body = json.loads(res.read())
                if self.action == "login":
                    self.auth_done.emit(True, body.get("token", ""), body.get("username", self.username))
                else:
                    self.auth_done.emit(True, "", self.email)
        except urllib.error.HTTPError as e:
            try:
                body = json.loads(e.read())
                if body.get("requires_verification"):
                    self.auth_done.emit(False, "requires_verification:" + body.get("email", ""), "")
                else:
                    self.auth_done.emit(False, body.get("error", "Request failed"), "")
            except Exception:
                self.auth_done.emit(False, "Request failed", "")
        except Exception as e:
            self.auth_done.emit(False, str(e), "")


class OTPWorker(QObject):
    """Background thread — handles email OTP validation and resending."""
    otp_done = pyqtSignal(bool, str)  # success, message/error

    def __init__(self, action: str, email: str, code: str = ""):
        super().__init__()
        self.action = action
        self.email  = email
        self.code   = code

    def start(self):
        threading.Thread(target=self.run, daemon=True).start()

    def run(self):
        try:
            url = f"{AUTH_API}/{self.action}"
            payload = {"email": self.email}
            if self.action == "verify-email":
                payload["code"] = self.code

            req = urllib.request.Request(
                url, data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json", "User-Agent": "MirageVPN/1.0"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as res:
                body = json.loads(res.read())
                self.otp_done.emit(True, body.get("message", "Success"))
        except urllib.error.HTTPError as e:
            try:
                body = json.loads(e.read())
                self.otp_done.emit(False, body.get("error", "Request failed"))
            except Exception:
                self.otp_done.emit(False, "Request failed")
        except Exception as e:
            self.otp_done.emit(False, str(e))


def format_bytes(b: int) -> str:
    if b < 1024:
        return f"{b} B"
    elif b < 1024 ** 2:
        return f"{b/1024:.1f} KB"
    else:
        return f"{b/1024**2:.2f} MB"


def _fmt_speed(mbps: float) -> str:
    """Format a speed in Mbps into human-readable string.

    <1 Mbps -> show Kbps (integer). >=1 Mbps -> show Mbps with 2 decimals.
    """
    kbps = mbps * 1000.0
    if kbps < 1000:
        return f"{kbps:.0f} Kbps"
    return f"{mbps:.2f} Mbps"


def _logo_path():
    for base in [
        getattr(sys, '_MEIPASS', None),
        os.path.dirname(os.path.abspath(__file__)),
        os.path.dirname(sys.argv[0]),
    ]:
        if base:
            p = os.path.join(base, 'assets', 'images', 'mirage new.png')
            if os.path.exists(p):
                return p
    return None

def _make_logo_pixmap(size: int, tint: QColor = QColor("#2A5AFF")) -> QPixmap:
    """Black-on-transparent PNG → tinted-on-transparent pixmap."""
    path = _logo_path()
    if not path:
        return QPixmap()
    src = QImage(path).convertToFormat(QImage.Format_ARGB32)
    src = src.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    w, h = src.width(), src.height()
    bits = src.bits()
    bits.setsize(w * h * 4)
    data = bytearray(bits)
    r, g, b = tint.red(), tint.green(), tint.blue()
    for i in range(w * h):
        base = i * 4
        if data[base + 3] > 0:      # non-transparent pixel → recolor
            data[base]     = b
            data[base + 1] = g
            data[base + 2] = r
            # alpha unchanged — preserves soft edges/anti-aliasing
    return QPixmap.fromImage(QImage(bytes(data), w, h, QImage.Format_ARGB32).copy())


class IPLookupWorker(QObject):
    """Background thread — fetches public IP, geo-location, and coordinates."""
    lookup_done = pyqtSignal(str, str, float, float)  # ip, location, lat, lon

    def __init__(self):
        super().__init__()

    def start(self):
        threading.Thread(target=self.run, daemon=True).start()

    def run(self):
        try:
            req = urllib.request.Request(
                "http://ip-api.com/json/?fields=query,city,country,lat,lon",
                headers={"User-Agent": "MirageVPN/1.0"}
            )
            with urllib.request.urlopen(req, timeout=6) as res:
                data = json.loads(res.read())
                ip   = data.get("query", "0.0.0.0")
                city = data.get("city", "")
                country = data.get("country", "")
                lat  = float(data.get("lat", 30.0))
                lon  = float(data.get("lon",  0.0))
                loc  = f"{city}, {country}" if city else country or "Unknown"
                self.lookup_done.emit(ip, loc, lat, lon)
        except Exception:
            self.lookup_done.emit("0.0.0.0", "Unknown", 30.0, 0.0)


# ── MAP CONSTANTS & HELPERS ──────────────────────────────────────────────────

def _geojson_path():
    for base in [
        getattr(sys, '_MEIPASS', None),
        os.path.dirname(os.path.abspath(__file__)),
        os.path.dirname(sys.argv[0]),
    ]:
        if base:
            p = os.path.join(base, 'assets', 'maps', 'world_map.json')
            if os.path.exists(p):
                return p
    return None


def _states_geojson_path():
    for base in [
        getattr(sys, '_MEIPASS', None),
        os.path.dirname(os.path.abspath(__file__)),
        os.path.dirname(sys.argv[0]),
    ]:
        if base:
            p = os.path.join(base, 'assets', 'maps', 'states_map.json')
            if os.path.exists(p):
                return p
    return None


def _cities_geojson_path():
    for base in [
        getattr(sys, '_MEIPASS', None),
        os.path.dirname(os.path.abspath(__file__)),
        os.path.dirname(sys.argv[0]),
    ]:
        if base:
            p = os.path.join(base, 'assets', 'maps', 'cities_map.json')
            if os.path.exists(p):
                return p
    return None


class GeoJsonLoader(QThread):
    """Loads GeoJSON features in background — no pixel mask."""
    features_ready = pyqtSignal(list)

    def __init__(self, path):
        super().__init__()
        self.path = path

    def run(self):
        try:
            with open(self.path, encoding='utf-8') as f:
                data = json.load(f)
            self.features_ready.emit(data.get('features', []))
        except Exception as e:
            print(f'[Map] GeoJSON load error: {e}')
            self.features_ready.emit([])


class MapRadarWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(280)
        self._lon_span = 30.0          # replaces BASE_LON_SPAN class constant
        self.grabGesture(Qt.PinchGesture)

        self._btn_plus  = QPushButton("+", self)
        self._btn_minus = QPushButton("−", self)
        _btn_style = """
            QPushButton {
                background: rgba(255,255,255,210);
                border: 1px solid rgba(0,0,0,35);
                border-radius: 8px;
                font-size: 18px; font-weight: 700;
                color: #1C1C1E;
            }
            QPushButton:pressed { background: rgba(210,218,230,255); }
        """
        self._btn_plus.setFixedSize(32, 32)
        self._btn_minus.setFixedSize(32, 32)
        self._btn_plus.setStyleSheet(_btn_style)
        self._btn_minus.setStyleSheet(_btn_style)
        self._btn_plus.clicked.connect(lambda: self._zoom(0.85))
        self._btn_minus.clicked.connect(lambda: self._zoom(1.15))

        # Floating brand logo
        self._logo_lbl = QLabel(self)
        self._logo_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        logo_pix = _make_logo_pixmap(74, QColor("#2A5AFF"))
        if not logo_pix.isNull():
            self._logo_lbl.setPixmap(logo_pix)
            self._logo_lbl.setFixedSize(74, 74)
        self._reposition_buttons()

        self._pulse        = 0.0
        self._is_connected = False
        self._features     = []
        self._state_features = []
        self._cities = []   # list of (name, lat, lon, pop) sorted by pop desc

        # Camera (animated via Qt properties)
        self._view_lon = 0.0
        self._view_lat = 30.0

        # Real location — set by IPLookupWorker result
        self._real_lon  = 0.0
        self._real_lat  = 30.0
        self._real_city = ""
        self._loc_set   = False

        # VPN server — Stockholm
        self._server_lon  = 18.0635
        self._server_lat  = 59.3326
        self._server_city = "Stockholm, Sweden"

        # Jet Animation state
        self._jet_lat      = 30.0
        self._jet_lon      = 0.0
        self._jet_angle    = 0.0
        self._jet_opacity  = 0.0
        self._jet_visible  = False
        self._jet_anim_grp = None
        self._pin_visible  = True
        self._jet_roll     = 0.0

        self._lon_anim = QPropertyAnimation(self, b"view_lon")
        self._lon_anim.setDuration(1600)
        self._lon_anim.setEasingCurve(QEasingCurve.InOutCubic)

        self._lat_anim = QPropertyAnimation(self, b"view_lat")
        self._lat_anim.setDuration(1600)
        self._lat_anim.setEasingCurve(QEasingCurve.InOutCubic)

        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._tick)
        self._pulse_timer.start(16) # 60 FPS

        gj = _geojson_path()
        if gj:
            self._builder = GeoJsonLoader(gj)
            self._builder.features_ready.connect(self._on_features_ready)
            self._builder.start()

        sj = _states_geojson_path()
        if sj:
            self._state_builder = GeoJsonLoader(sj)
            self._state_builder.features_ready.connect(self._on_state_features_ready)
            self._state_builder.start()

        cj = _cities_geojson_path()
        if cj:
            self._city_builder = GeoJsonLoader(cj)
            self._city_builder.features_ready.connect(self._on_cities_ready)
            self._city_builder.start()

    # ── Qt animated properties ───────────────────────────────────────────────
    def _get_vlon(self): return self._view_lon
    def _set_vlon(self, v): self._view_lon = v; self.update()
    view_lon = pyqtProperty(float, _get_vlon, _set_vlon)

    def _get_vlat(self): return self._view_lat
    def _set_vlat(self, v): self._view_lat = v; self.update()
    view_lat = pyqtProperty(float, _get_vlat, _set_vlat)

    def _get_jlat(self): return self._jet_lat
    def _set_jlat(self, v): self._jet_lat = v; self.update()
    jet_lat = pyqtProperty(float, _get_jlat, _set_jlat)

    def _get_jlon(self): return self._jet_lon
    def _set_jlon(self, v): self._jet_lon = v; self.update()
    jet_lon = pyqtProperty(float, _get_jlon, _set_jlon)

    def _get_jop(self): return self._jet_opacity
    def _set_jop(self, v): self._jet_opacity = v; self.update()
    jet_opacity = pyqtProperty(float, _get_jop, _set_jop)

    def _get_jroll(self): return self._jet_roll
    def _set_jroll(self, v): self._jet_roll = v; self.update()
    jet_roll = pyqtProperty(float, _get_jroll, _set_jroll)

    # Legacy compat — other code calls set_connected + zoom_level
    def _get_zoom(self): return 1.0 if self._is_connected else 0.0
    def _set_zoom(self, v): pass
    zoom_level = pyqtProperty(float, _get_zoom, _set_zoom)

    # ── Public API ───────────────────────────────────────────────────────────
    def set_real_location(self, lat: float, lon: float, city: str):
        self._real_lat, self._real_lon, self._real_city = lat, lon, city
        if not self._is_connected:
            if not self._loc_set:
                self._view_lat = lat   # snap on first call (no animation)
                self._view_lon = lon
                self.update()
            else:
                self._pan_to(lat, lon)
        self._loc_set = True

    def set_connected(self, connected: bool):
        self._is_connected = connected
        # Animations are now deferred to set_server_location/set_real_location 
        # after the IP lookup finishes, avoiding double-drop animations.

    def set_server_location(self, lat: float, lon: float, city: str):
        self._server_lat, self._server_lon, self._server_city = lat, lon, city
        if self._is_connected:
            self._pan_to(lat, lon)
            self.update()

    # ── Internals ────────────────────────────────────────────────────────────
    def _on_features_ready(self, features: list):
        self._features = features
        self.update()

    def _on_state_features_ready(self, features: list):
        self._state_features = features
        self.update()

    def _on_cities_ready(self, features: list):
        cities = []
        for feat in features:
            props = feat.get('properties', {})
            geom  = feat.get('geometry', {})
            if geom.get('type') != 'Point':
                continue
            lon, lat = geom['coordinates'][0], geom['coordinates'][1]
            name = props.get('name', '')
            pop  = int(props.get('pop_max', 0) or 0)
            if name:
                cities.append((name, lat, lon, pop))
        cities.sort(key=lambda x: -x[3])   # biggest cities first
        self._cities = cities
        self.update()

    def _pan_to(self, lat: float, lon: float):
        # Instead of a simple pan, we trigger the jet animation sequence
        self._animate_jet_transition(lat, lon)

    def _animate_jet_transition(self, target_lat: float, target_lon: float):
        if self._jet_anim_grp:
            self._jet_anim_grp.stop()

        old_lat, old_lon = self._view_lat, self._view_lon
        
        # Calculate Bezier control point for curved flight
        # Midpoint + perpendicular offset
        mid_lat = (old_lat + target_lat) / 2.0
        mid_lon = (old_lon + target_lon) / 2.0
        d_lat = target_lat - old_lat
        d_lon = target_lon - old_lon
        
        # Perpendicular vector (simple lat/lon space)
        # We offset it a bit to create a 'curve'
        curve_factor = 0.3 # curvature strength
        ctrl_lat = mid_lat - d_lon * curve_factor
        ctrl_lon = mid_lon + d_lat * curve_factor

        # Phase 1: Descent from top to current location
        self._jet_visible = True
        self._jet_angle = 180.0 # Flying down
        self._jet_roll = 0.0
        
        desc_start_lat = self._view_lat + (self._lon_span * 0.7)
        desc_start_lon = self._view_lon
        self._pin_visible = True

        anim_desc = QPropertyAnimation(self, b"jet_lat")
        anim_desc.setDuration(700)
        anim_desc.setStartValue(desc_start_lat)
        anim_desc.setEndValue(old_lat)
        anim_desc.setEasingCurve(QEasingCurve.OutQuad)

        anim_desc_lon = QPropertyAnimation(self, b"jet_lon")
        anim_desc_lon.setDuration(1)
        anim_desc_lon.setStartValue(old_lon)
        anim_desc_lon.setEndValue(old_lon)

        anim_fade_in = QPropertyAnimation(self, b"jet_opacity")
        anim_fade_in.setDuration(300)
        anim_fade_in.setStartValue(0.0)
        anim_fade_in.setEndValue(1.0)

        phase1 = QParallelAnimationGroup()
        phase1.addAnimation(anim_desc)
        phase1.addAnimation(anim_desc_lon)
        phase1.addAnimation(anim_fade_in)
        
        def phase1_end():
            self._pin_visible = False
            self.update()

        # Phase 2: Fade out at current location
        phase2 = QPropertyAnimation(self, b"jet_opacity")
        phase2.setDuration(250)
        phase2.setStartValue(1.0)
        phase2.setEndValue(0.0)

        # Phase 3: Global Flight (Map Pan + Bezier Jet Move)
        anim_pan_lat = QPropertyAnimation(self, b"view_lat")
        anim_pan_lat.setDuration(2200)
        anim_pan_lat.setStartValue(old_lat)
        anim_pan_lat.setEndValue(target_lat)
        anim_pan_lat.setEasingCurve(QEasingCurve.InOutCubic)

        anim_pan_lon = QPropertyAnimation(self, b"view_lon")
        anim_pan_lon.setDuration(2200)
        anim_pan_lon.setStartValue(old_lon)
        anim_pan_lon.setEndValue(target_lon)
        anim_pan_lon.setEasingCurve(QEasingCurve.InOutCubic)

        # Jet curved trajectory via a single variant animation tracking 't' (0-1)
        anim_flight = QVariantAnimation()
        anim_flight.setDuration(2200)
        anim_flight.setStartValue(0.0)
        anim_flight.setEndValue(1.0)
        anim_flight.setEasingCurve(QEasingCurve.InOutCubic)

        def update_flight(t):
            # Quadratic Bezier: (1-t)^2*P0 + 2(1-t)t*P1 + t^2*P2
            l1t = 1.0 - t
            self._jet_lat = (l1t**2 * old_lat) + (2 * l1t * t * ctrl_lat) + (t**2 * target_lat)
            self._jet_lon = (l1t**2 * old_lon) + (2 * l1t * t * ctrl_lon) + (t**2 * target_lon)
            
            # Calculate angle (tangent)
            # Derivative B'(t) = 2(1-t)(P1-P0) + 2t(P2-P1)
            dlat = 2 * (1-t) * (ctrl_lat - old_lat) + 2 * t * (target_lat - ctrl_lat)
            dlon = 2 * (1-t) * (ctrl_lon - old_lon) + 2 * t * (target_lon - ctrl_lon)
            self._jet_angle = math.degrees(math.atan2(dlon, dlat))
            
            # Add banking (roll) - max at mid-flight
            # We bank based on curvature, here simplified to a sine pulse
            self._jet_roll = math.sin(t * math.pi) * 35.0 # Max 35 deg roll
            self.update()

        anim_flight.valueChanged.connect(update_flight)
        
        anim_jet_op = QPropertyAnimation(self, b"jet_opacity")
        anim_jet_op.setDuration(400)
        anim_jet_op.setStartValue(0.0)
        anim_jet_op.setEndValue(1.0)

        phase3 = QParallelAnimationGroup()
        phase3.addAnimation(anim_pan_lat)
        phase3.addAnimation(anim_pan_lon)
        phase3.addAnimation(anim_flight)
        phase3.addAnimation(anim_jet_op)

        # Phase 4: Final Landing Fade
        phase4 = QPropertyAnimation(self, b"jet_opacity")
        phase4.setDuration(400)
        phase4.setStartValue(1.0)
        phase4.setEndValue(0.0)

        self._jet_anim_grp = QSequentialAnimationGroup()
        self._jet_anim_grp.addAnimation(phase1)
        self._jet_anim_grp.addAnimation(phase2)
        self._jet_anim_grp.addAnimation(phase3)
        self._jet_anim_grp.addAnimation(phase4)
        
        anim_desc.finished.connect(phase1_end)

        def on_done():
            self._jet_visible = False
            self._pin_visible = True
            self.update()
            if hasattr(self, "_logo_lbl"):
                 self._logo_lbl.show()

        self._jet_anim_grp.finished.connect(on_done)
        self._jet_anim_grp.start()

    def _tick(self):
        self._pulse = (self._pulse + 0.018) % 1.0
        self.update()

    def _zoom(self, factor: float):
        self._lon_span = max(2.0, min(180.0, self._lon_span * factor))
        self.update()

    def _reposition_buttons(self):
        self._btn_plus.move(self.width() - 42, 10)
        self._btn_minus.move(self.width() - 42, 48)
        if hasattr(self, "_logo_lbl"):
            self._logo_lbl.move((self.width() - self._logo_lbl.width()) // 2, 14)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_buttons()

    def wheelEvent(self, event):
        factor = 0.82 if event.angleDelta().y() > 0 else 1.22
        self._zoom(factor)

    def event(self, ev):
        if ev.type() == QEvent.Gesture:
            pinch = ev.gesture(Qt.PinchGesture)
            if pinch and pinch.scaleFactor():
                self._lon_span = max(2.0, min(180.0,
                    self._lon_span / pinch.scaleFactor()))
                self.update()
            return True
        return super().event(ev)

    def paintEvent(self, event):
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing, True)
        w, h    = self.width(), self.height()
        cx, cy  = w / 2.0, h / 2.0
        ppd     = w / self._lon_span      # pixels per degree
        spacing = 9
        dot_r   = 1.7
        hi_r    = min(w, h) * 0.30

        qp.fillRect(self.rect(), QColor("#F0F2F5"))

        # ── Country polygons ────────────────────────────────────────
        qp.setBrush(QColor(168, 182, 210, 130))
        qp.setPen(QPen(QColor(100, 125, 175, 160), 0.7))
        for feat in self._features:
            g      = feat.get('geometry', {})
            t      = g.get('type', '')
            coords = g.get('coordinates', [])
            polys  = [coords] if t == 'Polygon' else (coords if t == 'MultiPolygon' else [])
            for poly in polys:
                path  = QPainterPath()
                first = True
                for pt in poly[0]:
                    sx = cx + (pt[0] - self._view_lon) * ppd
                    sy = cy - (pt[1] - self._view_lat) * ppd
                    if first:
                        path.moveTo(sx, sy); first = False
                    else:
                        path.lineTo(sx, sy)
                path.closeSubpath()
                qp.drawPath(path)

        # ── State / province borders (only when zoomed in) ───────────
        if self._lon_span < 40.0 and self._state_features:
            opacity = max(0.0, min(1.0, (40.0 - self._lon_span) / 20.0))
            qp.setBrush(Qt.NoBrush)
            qp.setPen(QPen(QColor(90, 110, 160, int(130 * opacity)), 0.5))
            for feat in self._state_features:
                g      = feat.get('geometry', {})
                t      = g.get('type', '')
                coords = g.get('coordinates', [])
                polys  = [coords] if t == 'Polygon' else (coords if t == 'MultiPolygon' else [])
                for poly in polys:
                    path  = QPainterPath()
                    first = True
                    for pt in poly[0]:
                        sx = cx + (pt[0] - self._view_lon) * ppd
                        sy = cy - (pt[1] - self._view_lat) * ppd
                        if first:
                            path.moveTo(sx, sy); first = False
                        else:
                            path.lineTo(sx, sy)
                    path.closeSubpath()
                    qp.drawPath(path)

        # ── City labels ──────────────────────────────────────────────
        if self._lon_span < 25.0 and self._cities:
            if   self._lon_span < 5:   min_pop = 0
            elif self._lon_span < 8:   min_pop = 50_000
            elif self._lon_span < 12:  min_pop = 200_000
            elif self._lon_span < 18:  min_pop = 800_000
            else:                      min_pop = 4_000_000

            fade = max(0.0, min(1.0, (25.0 - self._lon_span) / 10.0))

            city_font = QFont(qp.font())
            city_font.setPixelSize(11)
            city_font.setWeight(QFont.Medium)
            qp.setFont(city_font)
            fm = QFontMetrics(city_font)

            for name, lat, lon, pop in self._cities:
                if pop < min_pop:
                    break               # sorted desc — safe to break early

                sx = cx + (lon - self._view_lon) * ppd
                sy = cy - (lat - self._view_lat) * ppd

                if sx < -60 or sx > w + 60 or sy < -20 or sy > h + 20:
                    continue            # off-screen, skip

                # Dot
                qp.setPen(Qt.NoPen)
                qp.setBrush(QColor(50, 80, 180, int(210 * fade)))
                qp.drawEllipse(QPointF(sx, sy), 2.8, 2.8)

                # Label (simple text)
                qp.setPen(QColor(80, 90, 120, int(220 * fade)))
                qp.drawText(int(sx + 8), int(sy + 4), name)
        grad = QRadialGradient(QPointF(cx, cy), hi_r)
        grad.setColorAt(0.0, QColor(88, 128, 218, 35))
        grad.setColorAt(1.0, QColor(88, 128, 218, 0))
        qp.setPen(Qt.NoPen)
        qp.setBrush(grad)
        qp.drawEllipse(QPointF(cx, cy), hi_r, hi_r)

        # Radar rings
        for off in (0.0, 0.33, 0.66):
            phase = (self._pulse + off) % 1.0
            qp.setBrush(Qt.NoBrush)
            qp.setPen(QPen(QColor(0, 102, 255, max(0, int(110 * (1.0 - phase)))), 1.5))
            qp.drawEllipse(QPointF(cx, cy), 6 + phase * 40, 6 + phase * 40)

        # Pin shadow
        qp.setPen(Qt.NoPen)
        qp.setBrush(QColor(0, 0, 0, 28))
        qp.drawEllipse(QPointF(cx + 2, cy + 14), 6, 3)

        # Pin teardrop
        if self._pin_visible:
            pp = QPainterPath()
            pp.moveTo(cx, cy + 12)
            pp.cubicTo(cx - 8, cy,      cx - 8, cy - 10, cx, cy - 14)
            pp.cubicTo(cx + 8, cy - 10, cx + 8, cy,      cx, cy + 12)
            qp.setBrush(QColor(0, 102, 255) if self._is_connected else QColor(220, 50, 50))
            qp.drawPath(pp)
            qp.setBrush(QColor(255, 255, 255, 215))
            qp.drawEllipse(QPointF(cx, cy - 4.5), 3.5, 3.5)

        # City label bubble
        label = self._server_city if self._is_connected else self._real_city
        if label and self._pin_visible:
            font = qp.font()
            font.setPixelSize(12)
            font.setWeight(QFont.DemiBold)
            qp.setFont(font)
            fm = QFontMetrics(font)
            tw = fm.boundingRect(label).width() + 24
            th = 26
            bx, by = cx - tw / 2, cy + 22
            qp.setBrush(QColor(255, 255, 255, 225))
            qp.setPen(Qt.NoPen)
            qp.drawRoundedRect(QRectF(bx, by, tw, th), 6, 6)
            qp.setPen(QColor(28, 28, 30, 220))
            qp.drawText(int(bx + 12), int(by + 17), label)

        # ── Fighter Jet Overlay ──────────────────────────────────────
        if self._jet_visible and self._jet_opacity > 0.01:
            jx = cx + (self._jet_lon - self._view_lon) * ppd
            jy = cy - (self._jet_lat - self._view_lat) * ppd
            
            # If it's too far off-screen, don't even worry, but jet_lat/lon 
            # are relative to the camera, so jx/jy will be screen coords
            
            qp.save()
            qp.translate(jx, jy)
            qp.rotate(self._jet_angle)
            qp.rotate(self._jet_roll) # apply banking
            qp.setOpacity(self._jet_opacity)
            
            # Jet body silhouette (sleek delta wing)
            path = QPainterPath()
            path.moveTo(0, -14)       # Nose
            path.lineTo(-10, 8)       # Left wing tip
            path.lineTo(-3, 6)        # Left engine area
            path.lineTo(0, 4)         # Tail dip
            path.lineTo(3, 6)         # Right engine area
            path.lineTo(10, 8)        # Right wing tip
            path.closeSubpath()
            
            # Glow/Shadow
            shadow_path = QPainterPath(path)
            qp.setBrush(QColor(0, 0, 0, 40))
            qp.drawPath(shadow_path.translated(2, 3))
            
            # Main Color (Steel/Blue)
            qp.setBrush(QColor(28, 48, 88))
            qp.setPen(QPen(QColor(0, 102, 255, 180), 1.2))
            qp.drawPath(path)
            
            # Cockpit glow
            qp.setBrush(QColor(100, 180, 255))
            qp.setPen(Qt.NoPen)
            qp.drawEllipse(QRectF(-1.5, -9, 3, 5))
            
            # Afterburner trail (very subtle pulses)
            if self._jet_opacity > 0.8:
                trail_h = (math.sin(time.time() * 20) + 1.0) * 4 + 8
                grad = QLinearGradient(0, 4, 0, 4 + trail_h)
                grad.setColorAt(0, QColor(255, 100, 0, 200))
                grad.setColorAt(1, QColor(255, 200, 0, 0))
                qp.setBrush(grad)
                qp.drawRect(QRectF(-1.5, 4, 3, trail_h))
            
            qp.restore()

        # Secondary home pin when connected (if visible on screen)
        if self._is_connected and self._pin_visible:
            hx = cx + (self._real_lon - self._view_lon) * ppd
            hy = cy - (self._real_lat - self._view_lat) * ppd
            if 10 < hx < w - 10 and 10 < hy < h - 10:
                hp = QPainterPath()
                hp.moveTo(hx, hy + 8)
                hp.cubicTo(hx - 5, hy,     hx - 5, hy - 7, hx, hy - 9)
                hp.cubicTo(hx + 5, hy - 7, hx + 5, hy,     hx, hy + 8)
                qp.setPen(Qt.NoPen)
                qp.setBrush(QColor(220, 50, 50, 190))
                qp.drawPath(hp)


class LoginScreen(QWidget):
    login_success = pyqtSignal(str, str)  # token, username

    def __init__(self):
        super().__init__()
        self.auth_worker = None
        self._loading_action = None
        self._current_mode = "login"
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignCenter)
        root.setContentsMargins(28, 28, 28, 28)

        shell = QFrame()
        shell.setObjectName("loginShell")
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        hero = QFrame()
        hero.setObjectName("heroPanel")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(24, 20, 24, 16)
        hero_layout.setSpacing(8)

        # Logo + brand row
        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        brand_row.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        logo_pix = _make_logo_pixmap(90, QColor("#2A5AFF"))
        if not logo_pix.isNull():
            logo_lbl = QLabel()
            logo_lbl.setPixmap(logo_pix)
            logo_lbl.setFixedSize(90, 90)
            brand_row.addWidget(logo_lbl)

        brand = QLabel("MIRAGE")
        brand.setObjectName("heroTitle")
        brand_row.addWidget(brand)

        hero_layout.addLayout(brand_row)

        tagline = QLabel("Network privacy with a ruthless edge.")
        tagline.setObjectName("heroSubtitle")
        tagline.setWordWrap(True)
        hero_layout.addWidget(tagline)

        hero_layout.addSpacing(6)
        badge_row = QHBoxLayout()
        badge_row.setSpacing(6)
        for label in [
            "AES-256 encrypted tunnel",
            "Kill switch fail-safe",
            "High anonymity routing",
        ]:
            badge = QLabel(label)
            badge.setObjectName("heroBadge")
            badge_row.addWidget(badge)
        badge_row.addStretch()
        hero_layout.addLayout(badge_row)

        form_host = QFrame()
        form_layout = QVBoxLayout(form_host)
        form_layout.setContentsMargins(24, 16, 24, 24)
        form_layout.setSpacing(10)

        title = QLabel("Secure Access")
        title.setObjectName("labelTitle")
        form_layout.addWidget(title)

        sub = QLabel("Choose a mode to continue")
        sub.setObjectName("labelSubtitle")
        form_layout.addWidget(sub)
        form_layout.addSpacing(8)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(8)
        self.btn_mode_login = QPushButton("SIGN IN")
        self.btn_mode_login.setCursor(Qt.PointingHandCursor)
        self.btn_mode_login.clicked.connect(lambda: self._set_mode("login"))
        mode_row.addWidget(self.btn_mode_login)
        self.btn_mode_register = QPushButton("REGISTER")
        self.btn_mode_register.setCursor(Qt.PointingHandCursor)
        self.btn_mode_register.clicked.connect(lambda: self._set_mode("register"))
        mode_row.addWidget(self.btn_mode_register)
        form_layout.addLayout(mode_row)

        self.auth_stack = QStackedWidget()

        login_tab = QWidget()
        lt = QVBoxLayout(login_tab)
        lt.setContentsMargins(0, 10, 0, 0)
        lt.setSpacing(8)

        self.login_user = QLineEdit()
        self.login_user.setPlaceholderText("Username or email")
        lt.addWidget(self.login_user)

        self.login_pass = QLineEdit()
        self.login_pass.setPlaceholderText("Password")
        self.login_pass.setEchoMode(QLineEdit.Password)
        self._attach_password_toggle(self.login_pass)
        lt.addWidget(self.login_pass)

        self.cb_save = QCheckBox("Remember Me")
        self.cb_save.setObjectName("cbSave")
        self.cb_save.setCursor(Qt.PointingHandCursor)
        lt.addWidget(self.cb_save)

        lt.addSpacing(4)
        self.login_msg = QLabel("")
        self.login_msg.setObjectName("labelError")
        self.login_msg.hide()
        lt.addWidget(self.login_msg)

        self.btn_login = QPushButton("SIGN IN")
        self.btn_login.setObjectName("btnPrimary")
        self.btn_login.setFixedHeight(46)
        self.btn_login.setCursor(Qt.PointingHandCursor)
        self.btn_login.clicked.connect(self._do_login)
        lt.addWidget(self.btn_login)
        self.login_user.returnPressed.connect(self._do_login)
        self.login_pass.returnPressed.connect(self._do_login)

        reg_tab = QWidget()
        rt = QVBoxLayout(reg_tab)
        rt.setContentsMargins(0, 10, 0, 0)
        rt.setSpacing(12)

        self.reg_user = QLineEdit()
        self.reg_user.setPlaceholderText("Username")
        rt.addWidget(self.reg_user)

        self.reg_email = QLineEdit()
        self.reg_email.setPlaceholderText("Email")
        rt.addWidget(self.reg_email)

        self.reg_pass = QLineEdit()
        self.reg_pass.setPlaceholderText("Password")
        self.reg_pass.setEchoMode(QLineEdit.Password)
        self._attach_password_toggle(self.reg_pass)
        rt.addWidget(self.reg_pass)

        self.reg_pass2 = QLineEdit()
        self.reg_pass2.setPlaceholderText("Confirm Password")
        self.reg_pass2.setEchoMode(QLineEdit.Password)
        self._attach_password_toggle(self.reg_pass2)
        rt.addWidget(self.reg_pass2)

        rt.addSpacing(4)
        self.reg_msg = QLabel("")
        self.reg_msg.setObjectName("labelError")
        self.reg_msg.hide()
        rt.addWidget(self.reg_msg)

        self.btn_register = QPushButton("CREATE ACCOUNT")
        self.btn_register.setObjectName("btnPrimary")
        self.btn_register.setFixedHeight(46)
        self.btn_register.setCursor(Qt.PointingHandCursor)
        self.btn_register.clicked.connect(self._do_register)
        rt.addWidget(self.btn_register)
        self.reg_user.returnPressed.connect(self._do_register)
        self.reg_email.returnPressed.connect(self._do_register)
        self.reg_pass.returnPressed.connect(self._do_register)
        self.reg_pass2.returnPressed.connect(self._do_register)

        verify_tab = QWidget()
        vt = QVBoxLayout(verify_tab)
        vt.setContentsMargins(0, 10, 0, 0)
        vt.setSpacing(12)

        self.verify_email_lbl = QLabel("Enter code sent to email")
        self.verify_email_lbl.setObjectName("labelSubtitle")
        self.verify_email_lbl.setAlignment(Qt.AlignCenter)
        vt.addWidget(self.verify_email_lbl)

        self.verify_code = QLineEdit()
        self.verify_code.setPlaceholderText("6-digit code")
        self.verify_code.setAlignment(Qt.AlignCenter)
        self.verify_code.setStyleSheet("font-size: 20px; letter-spacing: 6px; padding: 10px;")
        self.verify_code.setMaxLength(6)
        vt.addWidget(self.verify_code)

        vt.addSpacing(4)
        self.verify_msg = QLabel("")
        self.verify_msg.setObjectName("labelError")
        self.verify_msg.hide()
        vt.addWidget(self.verify_msg)

        self.btn_verify = QPushButton("VERIFY ACCOUNT")
        self.btn_verify.setObjectName("btnPrimary")
        self.btn_verify.setFixedHeight(46)
        self.btn_verify.setCursor(Qt.PointingHandCursor)
        self.btn_verify.clicked.connect(self._do_verify)
        vt.addWidget(self.btn_verify)
        self.verify_code.returnPressed.connect(self._do_verify)

        v_btn_row = QHBoxLayout()
        v_btn_row.setSpacing(8)
        self.btn_resend = QPushButton("Resend Code")
        self.btn_resend.setObjectName("btnGhost")
        self.btn_resend.setCursor(Qt.PointingHandCursor)
        self.btn_resend.clicked.connect(self._do_resend)
        v_btn_row.addWidget(self.btn_resend)

        self.btn_verify_back = QPushButton("Back to Login")
        self.btn_verify_back.setObjectName("btnGhost")
        self.btn_verify_back.setCursor(Qt.PointingHandCursor)
        self.btn_verify_back.clicked.connect(lambda: self._set_mode("login"))
        v_btn_row.addWidget(self.btn_verify_back)
        vt.addLayout(v_btn_row)

        self.auth_stack.addWidget(login_tab)
        self.auth_stack.addWidget(reg_tab)
        self.auth_stack.addWidget(verify_tab)
        form_layout.addWidget(self.auth_stack)

        shell_layout.addWidget(hero)
        shell_layout.addWidget(form_host, 1)
        root.addWidget(shell)

        self._set_mode("login")

    def _set_mode(self, mode: str, email: str = ""):
        self._current_mode = mode
        if mode == "login":
            self.auth_stack.setCurrentIndex(0)
            self.btn_mode_login.setObjectName("modeBtnActive")
            self.btn_mode_register.setObjectName("modeBtn")
            self.btn_mode_login.show()
            self.btn_mode_register.show()
        elif mode == "register":
            self.auth_stack.setCurrentIndex(1)
            self.btn_mode_login.setObjectName("modeBtn")
            self.btn_mode_register.setObjectName("modeBtnActive")
            self.btn_mode_login.show()
            self.btn_mode_register.show()
        elif mode == "verify":
            self.auth_stack.setCurrentIndex(2)
            self.btn_mode_login.hide()
            self.btn_mode_register.hide()
            self.verify_email_lbl.setText(f"Enter code sent to {email}")
            self.verify_email_lbl.setProperty("email", email)
            self.verify_code.setText("")
            self.verify_msg.hide()

        self.btn_mode_login.style().unpolish(self.btn_mode_login)
        self.btn_mode_login.style().polish(self.btn_mode_login)
        self.btn_mode_register.style().unpolish(self.btn_mode_register)
        self.btn_mode_register.style().polish(self.btn_mode_register)

    def _attach_password_toggle(self, field: QLineEdit):
        action = QAction("Show", field)
        field.addAction(action, QLineEdit.TrailingPosition)
        action.triggered.connect(lambda: self._toggle_password_visibility(field, action))

    def _toggle_password_visibility(self, field: QLineEdit, action: QAction):
        if field.echoMode() == QLineEdit.Password:
            field.setEchoMode(QLineEdit.Normal)
            action.setText("Hide")
        else:
            field.setEchoMode(QLineEdit.Password)
            action.setText("Show")

    def _set_loading(self, btn, loading: bool):
        if loading:
            self._loading_action = "login" if btn == self.btn_login else "register"
        elif self._loading_action == ("login" if btn == self.btn_login else "register"):
            self._loading_action = None

        self.btn_login.setEnabled(not loading and self._loading_action is None)
        self.btn_register.setEnabled(not loading and self._loading_action is None)
        self.btn_mode_login.setEnabled(self._loading_action is None)
        self.btn_mode_register.setEnabled(self._loading_action is None)

        btn.setEnabled(not loading)
        if loading:
            txt = "SIGNING IN..." if btn == self.btn_login else "CREATING ACCOUNT..."
            btn.setText(txt)
        else:
            btn.setText("SIGN IN" if btn == self.btn_login else "CREATE ACCOUNT")

    def _do_login(self):
        u = self.login_user.text().strip()
        p = self.login_pass.text()
        if not u or not p:
            self._show_error(self.login_msg, "Please fill all fields.")
            return
        self.login_msg.hide()
        self._set_loading(self.btn_login, True)
        self.auth_worker = AuthWorker("login", u, p)
        _keep_alive.append(self.auth_worker)
        self.auth_worker.auth_done.connect(self._on_login_done)
        self.auth_worker.start()

    def _do_register(self):
        u = self.reg_user.text().strip()
        e = self.reg_email.text().strip()
        p = self.reg_pass.text()
        p2 = self.reg_pass2.text()
        if not u or not e or not p or not p2:
            self._show_error(self.reg_msg, "Please fill all fields.")
            return
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", e):
            self._show_error(self.reg_msg, "Please enter a valid email address.")
            return
        if p != p2:
            self._show_error(self.reg_msg, "Passwords do not match.")
            return
        if len(p) < 6:
            self._show_error(self.reg_msg, "Password must be at least 6 characters.")
            return
        self.reg_msg.hide()
        self._set_loading(self.btn_register, True)
        self.auth_worker = AuthWorker("register", u, p, e)
        _keep_alive.append(self.auth_worker)
        self.auth_worker.auth_done.connect(self._on_register_done)
        self.auth_worker.start()

    def _on_login_done(self, success, token, username):
        self._set_loading(self.btn_login, False)
        if success:
            if self.cb_save.isChecked():
                settings = QSettings("Mirage", "MirageVPN")
                settings.setValue("auth_token", token)
                settings.setValue("auth_user", username)
                settings.setValue("remember_me", True)
            QTimer.singleShot(10, lambda: self.login_success.emit(token, username))
        else:
            if token.startswith("requires_verification:"):
                email = token.split(":")[1]
                self._set_mode("verify", email)
                self._show_info(self.verify_msg, "Please verify your email to log in.")
            else:
                self._show_error(self.login_msg, token)

    def _on_register_done(self, success, token, email):
        self._set_loading(self.btn_register, False)
        if success:
            self._set_mode("verify", email)
            self._show_info(self.verify_msg, "Account created! Please verify your email.")
        else:
            self._show_error(self.reg_msg, token)

    def _do_verify(self):
        code = self.verify_code.text().strip()
        email = self.verify_email_lbl.property("email")
        if len(code) != 6 or not code.isdigit():
            self._show_error(self.verify_msg, "Please enter a 6-digit code.")
            return
        
        self.verify_msg.hide()
        self.btn_verify.setEnabled(False)
        self.btn_verify.setText("VERIFYING...")
        self.otp_worker = OTPWorker("verify-email", email, code)
        _keep_alive.append(self.otp_worker)
        self.otp_worker.otp_done.connect(self._on_verify_done)
        self.otp_worker.start()

    def _on_verify_done(self, success, msg):
        self.btn_verify.setEnabled(True)
        self.btn_verify.setText("VERIFY ACCOUNT")
        if success:
            self._set_mode("login")
            self._show_info(self.login_msg, msg)
        else:
            self._show_error(self.verify_msg, msg)

    def _do_resend(self):
        email = self.verify_email_lbl.property("email")
        self.btn_resend.setEnabled(False)
        self.btn_resend.setText("SENDING...")
        self.otp_worker = OTPWorker("resend-code", email)
        _keep_alive.append(self.otp_worker)
        self.otp_worker.otp_done.connect(self._on_resend_done)
        self.otp_worker.start()

    def _on_resend_done(self, success, msg):
        self.btn_resend.setEnabled(True)
        self.btn_resend.setText("Resend Code")
        if success:
            self._show_info(self.verify_msg, msg)
        else:
            self._show_error(self.verify_msg, msg)

    def _show_error(self, label, msg):
        label.setObjectName("labelError")
        label.style().unpolish(label)
        label.style().polish(label)
        label.setText(msg)
        label.show()

    def _show_info(self, label, msg):
        label.setObjectName("labelSuccess")
        label.style().unpolish(label)
        label.style().polish(label)
        label.setText(msg)
        label.show()


class MainScreen(QWidget):
    logout_requested = pyqtSignal()

    def __init__(self, token: str, username: str):
        super().__init__()
        self._restore_firewall_on_startup()
        self.token = token
        self.username = username
        self.settings = QSettings("Mirage", "MirageVPN")
        self.vpn_worker = None
        self.connected = False
        self._connecting = False
        self._connect_anim_step = 0
        self._last_bytes_time = None
        self._bw_up = []
        self._bw_down = []
        self._build_ui()
        self._refresh_ip()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), QColor("#F0F2F5"))

        blobs = [
            (QPointF(self.width() * 0.20, self.height() * 0.30), QColor(180, 210, 255, 50), 300),
            (QPointF(self.width() * 0.80, self.height() * 0.20), QColor(220, 200, 240, 40), 250),
            (QPointF(self.width() * 0.50, self.height() * 0.85), QColor(200, 230, 250, 35), 280),
        ]

        for center, color, radius in blobs:
            grad = QRadialGradient(center, radius)
            grad.setColorAt(0.0, color)
            grad.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 0))
            painter.setBrush(grad)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(center, radius, radius)

        super().paintEvent(event)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 24)
        root.setSpacing(16)

        # ── Map section (takes most of the vertical space) ──
        self.map_widget = MapRadarWidget()
        root.addWidget(self.map_widget, 1)

        # ── Content area below map ──
        content = QVBoxLayout()
        content.setContentsMargins(24, 0, 24, 0)
        content.setSpacing(16)

        # ── Disconnected view: location selector + connect row ──
        self.disconnected_widget = QWidget()
        disc_layout = QVBoxLayout(self.disconnected_widget)
        disc_layout.setContentsMargins(0, 0, 0, 0)
        disc_layout.setSpacing(14)

        # Location selector card
        loc_card = QFrame()
        loc_card.setObjectName("locationSelector")
        loc_card.setCursor(Qt.PointingHandCursor)
        loc_layout = QHBoxLayout(loc_card)
        loc_layout.setContentsMargins(20, 18, 20, 18)
        loc_layout.setSpacing(14)

        loc_shadow = QGraphicsDropShadowEffect(loc_card)
        loc_shadow.setOffset(0, 4)
        loc_shadow.setColor(QColor(0, 0, 0, 18))
        loc_shadow.setBlurRadius(20)
        loc_card.setGraphicsEffect(loc_shadow)

        globe_icon = QLabel("\U0001F310")
        globe_icon.setStyleSheet("font-size: 22px;")
        loc_layout.addWidget(globe_icon)

        loc_text = QLabel("\U0001F1F8\U0001F1EA  Stockholm, Sweden")
        loc_text.setStyleSheet("font-size: 16px; color: #1C1C1E; font-weight: 500;")
        loc_layout.addWidget(loc_text)
        loc_layout.addStretch()

        chevron = QLabel("\u25BC")
        chevron.setStyleSheet("font-size: 14px; color: #C7C7CC;")
        loc_layout.addWidget(chevron)

        # Dropdown menu
        self.server_menu = QMenu(self)
        self.server_menu.setStyleSheet(
            "QMenu { background: white; border-radius: 10px; border: 1px solid #E5E5EA; padding: 10px; }"
            "QMenu::item { padding: 12px 36px; border-radius: 8px; color: #1C1C1E; font-size: 16px; font-weight: 500; }"
            "QMenu::item:selected { background: rgba(0, 102, 255, 0.08); color: #0066FF; }"
        )
        # We only have one server currently
        sweden_action = self.server_menu.addAction("\U0001F1F8\U0001F1EA  Stockholm, Sweden")
        sweden_action.triggered.connect(lambda: loc_text.setText("\U0001F1F8\U0001F1EA  Stockholm, Sweden"))

        def show_menu(event):
            if event.button() == Qt.LeftButton:
                self.server_menu.exec_(loc_card.mapToGlobal(QPoint(0, loc_card.height() + 4)))
        
        loc_card.mousePressEvent = show_menu

        disc_layout.addWidget(loc_card)

        # Bottom row: VPN Server label + Connect button
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)

        server_info = QVBoxLayout()
        server_info.setSpacing(2)
        
        real_header = QHBoxLayout()
        real_header.setSpacing(6)
        
        self.lbl_real_location = QLabel("Your Location")
        self.lbl_real_location.setStyleSheet("font-size: 13px; color: #8E8E93; font-weight: 500;")
        real_header.addWidget(self.lbl_real_location)
        
        self.lbl_real_ip = QLabel("...")
        self.lbl_real_ip.setStyleSheet("font-size: 13px; color: #FF3B30; font-weight: 600;")
        real_header.addWidget(self.lbl_real_ip)
        real_header.addStretch()
        
        server_info.addLayout(real_header)

        self.status_label = QLabel("Disconnected")
        self.status_label.setStyleSheet("font-size: 18px; color: #1C1C1E; font-weight: 600;")
        server_info.addWidget(self.status_label)

        bottom_row.addLayout(server_info)
        bottom_row.addStretch()

        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setObjectName("btnConnect")
        self.btn_connect.setCursor(Qt.PointingHandCursor)
        self.btn_connect.setMinimumWidth(140)
        self.btn_connect.setFixedHeight(50)
        self.btn_connect.clicked.connect(self._toggle_connection)

        self.btn_connect_glow = QGraphicsDropShadowEffect(self.btn_connect)
        self.btn_connect_glow.setOffset(0, 4)
        self.btn_connect_glow.setColor(QColor(0, 102, 255, 90))
        self.btn_connect_glow.setBlurRadius(24)
        self.btn_connect.setGraphicsEffect(self.btn_connect_glow)

        bottom_row.addWidget(self.btn_connect)
        disc_layout.addLayout(bottom_row)

        # ── Connected view: telemetry + session bar ──
        self.connected_widget = QWidget()
        conn_layout = QVBoxLayout(self.connected_widget)
        conn_layout.setContentsMargins(0, 0, 0, 0)
        conn_layout.setSpacing(14)

        self.bw_graph = BandwidthGraph(self.map_widget)
        self.bw_graph.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.bw_graph.setVisible(False)

        # Session controller bar
        session_row = QHBoxLayout()
        session_row.setSpacing(10)

        sess_info = QVBoxLayout()
        sess_info.setSpacing(2)

        sess_header = QHBoxLayout()
        sess_header.setSpacing(6)
        sess_label = QLabel("VPN Server")
        sess_label.setStyleSheet("font-size: 13px; color: #8E8E93; font-weight: 500;")
        sess_header.addWidget(sess_label)
        
        self.lbl_session_ip = QLabel("...")
        self.lbl_session_ip.setStyleSheet("font-size: 13px; color: #0066FF; font-weight: 600;")
        sess_header.addWidget(self.lbl_session_ip)
        sess_header.addStretch()

        sess_info.addLayout(sess_header)

        self.lbl_server_name = QLabel("\U0001F1F8\U0001F1EA  Stockholm, Sweden")
        self.lbl_server_name.setStyleSheet("font-size: 16px; color: #1C1C1E; font-weight: 600;")
        sess_info.addWidget(self.lbl_server_name)

        session_row.addLayout(sess_info)
        session_row.addStretch()

        # Connected badge with timer
        self.lbl_connected_badge = QLabel("Connected  00:00")
        self.lbl_connected_badge.setStyleSheet(
            "background: rgba(0,0,0,0.06); color: #1C1C1E; font-size: 14px; font-weight: 600;"
            "padding: 10px 20px; border-radius: 18px;"
        )
        session_row.addWidget(self.lbl_connected_badge)

        # Red disconnect button
        self.btn_disconnect = QPushButton("\u23FB")
        self.btn_disconnect.setObjectName("btnDisconnect")
        self.btn_disconnect.setCursor(Qt.PointingHandCursor)
        self.btn_disconnect.setToolTip("Disconnect")
        self.btn_disconnect.clicked.connect(self._disconnect)
        session_row.addWidget(self.btn_disconnect)

        conn_layout.addLayout(session_row)

        # Initially hide connected widget
        self.connected_widget.hide()

        content.addWidget(self.disconnected_widget)
        content.addWidget(self.connected_widget)
        root.addLayout(content)

        # Quick Actions Dock
        dock = QFrame()
        dock.setObjectName("bottomDock")
        dock.setStyleSheet(
            "QFrame#bottomDock { background: rgba(0,0,0,0.03); border-radius: 18px; }"
            "QToolButton { font-size: 14px; font-weight: 600; background: rgba(0,0,0,0.04); color: #8E8E93; padding: 8px 16px; border-radius: 10px; border: none; }"
            "QToolButton:hover { background: rgba(0,0,0,0.08); color: #1C1C1E; }"
            "QCheckBox { font-size: 14px; font-weight: 600; color: #1C1C1E; }"
            "QCheckBox::indicator { width: 16px; height: 16px; border-radius: 5px; border: 1px solid #C7C7CC; background: white; }"
            "QCheckBox::indicator:checked { background: #0066FF; border: 1px solid #0066FF; }"
        )
        dock_layout = QHBoxLayout(dock)
        dock_layout.setContentsMargins(20, 16, 20, 16)
        dock_layout.setSpacing(18)

        self.btn_dashboard = QToolButton()
        self.btn_dashboard.setText("\u2630  Logs")
        self.btn_dashboard.setToolTip("View Dashboard & Logs")
        self.btn_dashboard.setCursor(Qt.PointingHandCursor)
        self.btn_dashboard.clicked.connect(self._open_dashboard)
        dock_layout.addWidget(self.btn_dashboard)

        dock_layout.addStretch()

        self.toggle_ks = QCheckBox("Kill Switch")
        self.toggle_ks.setCursor(Qt.PointingHandCursor)
        self.toggle_ks.toggled.connect(self._on_ks_toggled)
        dock_layout.addWidget(self.toggle_ks)

        self.toggle_anon = QCheckBox("Tor Mode")
        self.toggle_anon.setCursor(Qt.PointingHandCursor)
        self.toggle_anon.toggled.connect(self._on_anon_toggled)
        dock_layout.addWidget(self.toggle_anon)

        root.addWidget(dock)

        # Hidden widgets for compatibility
        self.lbl_ip = QLabel("")
        self.lbl_ip.hide()
        self.lbl_location = QLabel("")
        self.lbl_location.hide()
        self.lbl_duration = QLabel("")
        self.lbl_duration.hide()
        self.rate_label = QLabel("")
        self.rate_label.hide()
        self.error_label = QLabel("")
        self.error_label.setObjectName("labelError")
        self.error_label.hide()

        self.connect_time = None
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_timer)
        self.timer.setInterval(1000)

        self.connect_anim_timer = QTimer()
        self.connect_anim_timer.timeout.connect(self._animate_connecting_label)
        self.connect_anim_timer.setInterval(350)

        self.connect_pulse = QPropertyAnimation(self.btn_connect_glow, b"blurRadius", self)
        self.connect_pulse.setStartValue(16.0)
        self.connect_pulse.setEndValue(30.0)
        self.connect_pulse.setDuration(1300)
        self.connect_pulse.setEasingCurve(QEasingCurve.InOutSine)
        self.connect_pulse.setLoopCount(-1)

        self.toast = QLabel("", self)
        self.toast.hide()
        self.toast.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.toast.setAlignment(Qt.AlignCenter)
        self.toast.setStyleSheet(
            "padding: 8px 12px; border-radius: 8px;"
            "background: #F8FAFF; color: #253047; border: 1px solid #DDE5F3;"
            "font-size: 11px; font-weight: 600;"
        )
        self.toast_effect = QGraphicsOpacityEffect(self.toast)
        self.toast.setGraphicsEffect(self.toast_effect)
        self.toast_effect.setOpacity(0.0)
        self.toast_hold_timer = QTimer(self)
        self.toast_hold_timer.setSingleShot(True)
        self.toast_hold_timer.timeout.connect(self._fade_out_toast)

        self.lbl_up = QLabel("0 B")
        self.lbl_down = QLabel("0 B")
        self.lbl_mode = QLabel("Standard")

        self._load_preferences()
        self._start_idle_pulse()

        self._ip_worker = IPLookupWorker()
        self._ip_worker.lookup_done.connect(self._on_ip_result)
        self._ip_worker.start()

    def _open_dashboard(self):
        try:
            self._dash_win = DashboardScreen(self.token)
            self._dash_win.show()
        except Exception as e:
            self._show_toast(f"Cannot open dashboard: {e}", "error")

    def _position_bandwidth_graph(self):
        if not hasattr(self, "bw_graph") or not hasattr(self, "map_widget"):
            return
        if self.bw_graph.parent() is not self.map_widget:
            self.bw_graph.setParent(self.map_widget)

        margin_x = 18
        margin_bottom = 14
        graph_height = 150
        width = max(180, self.map_widget.width() - (margin_x * 2))
        width = min(width, 900)
        x = max(margin_x, (self.map_widget.width() - width) // 2)
        y = max(10, self.map_widget.height() - graph_height - margin_bottom)
        self.bw_graph.setGeometry(x, y, width, graph_height)
        self.bw_graph.raise_()

    def _on_ip_result(self, ip: str, location: str, lat: float, lon: float):
        self.lbl_ip.setText(f"IP: {ip}")
        self.lbl_location.setText(f"Location: {location}")
        self._current_ip = ip
        if self.connected:
            # If in Tor mode or we want to prioritize country, clean up the label
            display_loc = location
            if self.toggle_anon.isChecked() and "," in location:
                display_loc = location.split(",")[-1].strip()

            if hasattr(self, 'lbl_server_name'):
                self.lbl_server_name.setText(f"\U0001F310  {display_loc}")
            if hasattr(self, 'lbl_session_ip'):
                self.lbl_session_ip.setText(f"  \u2022  {ip}")
            
            # Update map target to the actual proxy location
            self.map_widget.set_server_location(lat, lon, display_loc)
        else:
            if hasattr(self, 'lbl_real_location'):
                self.lbl_real_location.setText(location)
            if hasattr(self, 'lbl_real_ip'):
                self.lbl_real_ip.setText(f"  \u2022  {ip}")
            # Tell map widget where user actually is
            self.map_widget.set_real_location(lat, lon, location)
        
        # Ensure the title bar updates its badge text


    def _refresh_ip(self):
        """Re-fetch public IP and location."""
        self.lbl_ip.setText("IP: ...")
        self.lbl_location.setText("Location: ...")
        if hasattr(self, 'lbl_real_ip'):
            self.lbl_real_ip.setText("  •  ...")
        if hasattr(self, 'lbl_real_location'):
            self.lbl_real_location.setText("Fetching...")
        self._ip_worker = IPLookupWorker()
        _keep_alive.append(self._ip_worker)
        self._ip_worker.lookup_done.connect(self._on_ip_result)
        self._ip_worker.start()

    def _toggle_connection(self):
        if not self.connected:
            self._connect()
        else:
            self._disconnect()

    def _connect(self):
        # Switch button to red CANCEL immediately
        self.btn_connect.setObjectName("btnCancel")
        self.btn_connect.setText("Cancel")
        self.btn_connect.setEnabled(True)
        self.btn_connect.style().unpolish(self.btn_connect)
        self.btn_connect.style().polish(self.btn_connect)
        self.btn_connect.clicked.disconnect()
        self.btn_connect.clicked.connect(self._cancel_connect)

        self.status_label.setText("Connecting...")
        self._connect_anim_step = 0
        self.connect_anim_timer.start()
        self._stop_idle_pulse()
        self.error_label.hide()
        self.toggle_anon.setEnabled(False)
        self._reset_transfer_metrics()
        self._show_toast("Connecting to Mirage...", level="info")
        self._connecting = True
        self._bw_up.clear()
        self._bw_down.clear()

        tor = self.toggle_anon.isChecked()

        def do_connect():
            try:
                from wintun_client import WintunClient
                self.wintun_client = WintunClient(self.token, tor_mode=tor)
                def _bw_cb(up_mbps, down_mbps):
                    QMetaObject.invokeMethod(
                        self,
                        "_on_bandwidth",
                        Qt.QueuedConnection,
                        Q_ARG(float, up_mbps),
                        Q_ARG(float, down_mbps),
                    )
                self.wintun_client.on_bandwidth = _bw_cb
                self.wintun_client.connect()
                if self._connecting:
                    QMetaObject.invokeMethod(self, "_on_tun_connected", Qt.QueuedConnection)
            except Exception as e:
                if self._connecting:
                    if hasattr(self, 'wintun_client') and self.wintun_client:
                        try:
                            self.wintun_client.disconnect()
                        except Exception:
                            pass
                    QMetaObject.invokeMethod(
                        self, "_on_tun_error",
                        Qt.QueuedConnection,
                        Q_ARG(str, str(e))
                    )

        threading.Thread(target=do_connect, daemon=True).start()

    def _cancel_connect(self):
        self._connecting = False
        if hasattr(self, 'wintun_client') and self.wintun_client:
            client = self.wintun_client
            self.wintun_client = None
            threading.Thread(target=client.disconnect, daemon=True).start()
        self._apply_disconnected()
        # Restore button click handler
        self.btn_connect.clicked.disconnect()
        self.btn_connect.clicked.connect(self._toggle_connection)
        self._show_toast("Connection cancelled", level="info")

    def _disconnect(self):
        if hasattr(self, 'wintun_client') and self.wintun_client:
            client = self.wintun_client
            self.wintun_client = None
            threading.Thread(target=client.disconnect, daemon=True).start()
        self._apply_disconnected()
        if self.toggle_ks.isChecked():
            self._kill_switch_off()
        self._show_toast("VPN disconnected", level="info")
        self._refresh_ip()

    @pyqtSlot()
    def _on_tun_connected(self):
        self.connected = True
        self._connecting = False
        self.connect_anim_timer.stop()
        # Switch to connected view
        self.disconnected_widget.hide()
        self.connected_widget.show()
        self.map_widget.set_connected(True)
        # Update title bar badge

        self.connect_time = time.time()
        self._last_bytes_time = self.connect_time
        self.bw_graph.setVisible(True)
        self._position_bandwidth_graph()
        self.timer.start()
        self.toggle_anon.setEnabled(False)
        self._show_toast("VPN connected — Fetching IP...", level="success")
        self._refresh_ip()

    @pyqtSlot(str)
    def _on_tun_error(self, msg: str):
        self._connecting = False
        self._apply_disconnected()
        self.btn_connect.clicked.disconnect()
        self.btn_connect.clicked.connect(self._toggle_connection)
        self.error_label.setText(f"Error: {msg}")
        self.error_label.show()
        self._show_toast(msg, level="error")

    def _animate_connecting_label(self):
        dots = "." * ((self._connect_anim_step % 3) + 1)
        self.status_label.setText(f"Connecting{dots}")
        self._connect_anim_step += 1

    def _apply_disconnected(self):
        self.connected = False
        self.connect_anim_timer.stop()
        self.timer.stop()
        self.connect_time = None
        # Switch back to disconnected view
        self.connected_widget.hide()
        self.disconnected_widget.show()
        self.map_widget.set_connected(False)
        if hasattr(self, "bw_graph"):
            self.bw_graph.setVisible(False)
            self.bw_graph.raise_()

        self.btn_connect.setObjectName("btnConnect")
        self.btn_connect.setText("Connect")
        self.btn_connect.setEnabled(True)
        self.btn_connect.style().unpolish(self.btn_connect)
        self.btn_connect.style().polish(self.btn_connect)
        self.btn_connect.clicked.disconnect()
        self.btn_connect.clicked.connect(self._toggle_connection)
        self.status_label.setText("Disconnected")
        self.toggle_anon.setEnabled(True)
        self._reset_transfer_metrics()
        self._start_idle_pulse()

    def _reset_transfer_metrics(self):
        self._last_bytes_time = None
        self.lbl_up.setText("0.0 Mbps")
        self.lbl_down.setText("0.0 Mbps")
        self.rate_label.setText("UP 0.0 Mbps | DOWN 0.0 Mbps")
        self._bw_up.clear()
        self._bw_down.clear()
        if hasattr(self, "bw_graph"):
            self.bw_graph.update_data(self._bw_up, self._bw_down)

    @pyqtSlot(float, float)
    def _on_bandwidth(self, up_mbps: float, down_mbps: float):
        self._bw_up.append(up_mbps)
        self._bw_down.append(down_mbps)
        if len(self._bw_up) > 60:
            self._bw_up.pop(0)
            self._bw_down.pop(0)
        if hasattr(self, "bw_graph"):
            self.bw_graph.update_data(self._bw_up, self._bw_down)
        # Keep cached current values in sync so no other poll overwrites live numbers
        self._current_upload = up_mbps
        self._current_download = down_mbps

        # Adaptive unit formatting
        up_text = _fmt_speed(up_mbps)
        down_text = _fmt_speed(down_mbps)
        self.lbl_up.setText(up_text)
        self.lbl_down.setText(down_text)
        self.rate_label.setText(f"UP {up_text} | DOWN {down_text}")



    def _start_idle_pulse(self):
        self.btn_connect_glow.setEnabled(True)
        self.btn_connect_glow.setColor(QColor(0, 102, 255, 90))
        if self.connect_pulse.state() != QAbstractAnimation.Running:
            self.connect_pulse.start()

    def _stop_idle_pulse(self):
        if self.connect_pulse.state() == QAbstractAnimation.Running:
            self.connect_pulse.stop()
        self.btn_connect_glow.setBlurRadius(16)

    def _on_ks_toggled(self, checked: bool):
        self.settings.setValue("kill_switch", checked)
        self._show_toast("Kill Switch enabled" if checked else "Kill Switch disabled", level="info")

    def _on_anon_toggled(self, checked: bool):
        self.settings.setValue("high_anonymity", checked)
        self.lbl_mode.setText("High Anon" if checked else "Standard")
        self._show_toast("High Anonymity enabled" if checked else "High Anonymity disabled", level="info")

    def _load_preferences(self):
        def to_bool(value):
            if isinstance(value, bool):
                return value
            return str(value).strip().lower() in ("1", "true", "yes", "on")

        ks = to_bool(self.settings.value("kill_switch", False))
        anon = to_bool(self.settings.value("high_anonymity", False))

        self.toggle_ks.blockSignals(True)
        self.toggle_anon.blockSignals(True)
        self.toggle_ks.setChecked(ks)
        self.toggle_anon.setChecked(anon)
        self.toggle_ks.blockSignals(False)
        self.toggle_anon.blockSignals(False)

    def _show_toast(self, message: str, level: str = "info", hold_ms: int = 2200):
        palettes = {
            "info": ("#1E2A3D", "#F8FAFF", "#DDE5F3"),
            "success": ("#0E9F6E", "#E7FBF2", "#BEEEDC"),
            "error": ("#BE123C", "#FFF0F3", "#F4C8D4"),
        }
        fg, bg, bd = palettes.get(level, palettes["info"])
        self.toast.setStyleSheet(
            "padding: 8px 12px; border-radius: 8px;"
            f"background: {bg}; color: {fg}; border: 1px solid {bd};"
            "font-size: 11px; font-weight: 600;"
        )
        self.toast.setText(message)
        self.toast.adjustSize()
        self._position_toast()
        self.toast.show()

        if hasattr(self, "toast_fade_in") and self.toast_fade_in.state() == QAbstractAnimation.Running:
            self.toast_fade_in.stop()
        if hasattr(self, "toast_fade_out") and self.toast_fade_out.state() == QAbstractAnimation.Running:
            self.toast_fade_out.stop()

        self.toast_effect.setOpacity(0.0)
        self.toast_fade_in = QPropertyAnimation(self.toast_effect, b"opacity", self)
        self.toast_fade_in.setDuration(170)
        self.toast_fade_in.setStartValue(0.0)
        self.toast_fade_in.setEndValue(1.0)
        self.toast_fade_in.start()

        self.toast_hold_timer.start(hold_ms)

    def _fade_out_toast(self):
        self.toast_fade_out = QPropertyAnimation(self.toast_effect, b"opacity", self)
        self.toast_fade_out.setDuration(220)
        self.toast_fade_out.setStartValue(self.toast_effect.opacity())
        self.toast_fade_out.setEndValue(0.0)
        self.toast_fade_out.finished.connect(self.toast.hide)
        self.toast_fade_out.start()

    def _position_toast(self):
        self.toast.adjustSize()
        x = max(12, (self.width() - self.toast.width()) // 2)
        y = max(12, self.height() - self.toast.height() - 16)
        self.toast.move(x, y)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "toast"):
            self._position_toast()
        self._position_bandwidth_graph()

    def _update_timer(self):
        if self.connect_time:
            elapsed = int(time.time() - self.connect_time)
            m, s = divmod(elapsed, 60)
            h, m = divmod(m, 60)
            if h > 0:
                time_str = f"{h:02d}:{m:02d}:{s:02d}"
            else:
                time_str = f"{m:02d}:{s:02d}"
            self.lbl_connected_badge.setText(f"Connected  {time_str}")

    def _restore_firewall_on_startup(self):
        """Always restore firewall on app launch - safety net for crashes."""
        if platform.system() == "Windows":
            subprocess.run(
                ['netsh', 'advfirewall', 'set', 'allprofiles',
                 'firewallpolicy', 'blockinbound,allowoutbound'],
                capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
            )

    def _kill_switch_on(self):
        """Block all internet traffic."""
        if platform.system() == "Windows":
            subprocess.run(
                ['netsh', 'advfirewall', 'set', 'allprofiles',
                 'firewallpolicy', 'blockinbound,blockoutbound'],
                capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            with open("ks_active.flag", "w") as f:
                f.write("1")

    def _kill_switch_off(self):
        """Restore normal internet traffic."""
        if platform.system() == "Windows":
            subprocess.run(
                ['netsh', 'advfirewall', 'set', 'allprofiles',
                 'firewallpolicy', 'blockinbound,allowoutbound'],
                capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            if os.path.exists("ks_active.flag"):
                os.remove("ks_active.flag")

    def _open_dashboard(self):
        self.dashboard = DashboardScreen(self.token)
        self.dashboard.show()

    def _do_logout(self):
        if self.connected:
            self._disconnect()
        self.logout_requested.emit()


def relative_time(ts_str: str) -> str:
    """Convert ISO timestamp to '2 hours ago' style string."""
    try:
        from datetime import datetime, timezone
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = int((now - ts).total_seconds())
        if diff < 60:
            return "just now"
        elif diff < 3600:
            return f"{diff // 60}m ago"
        elif diff < 86400:
            return f"{diff // 3600}h ago"
        else:
            return f"{diff // 86400}d ago"
    except Exception:
        return ts_str[:16].replace("T", " ")


def pair_sessions(logs: list) -> list:
    """
    Match connect/disconnect pairs to compute session durations.
    Returns a list of dicts with 'duration_secs' added to connect events.
    """
    from datetime import datetime
    result = []
    pending = {}  # user_id -> connect log

    for log in reversed(logs):  # oldest first
        uid = log.get("user_id", "")
        event = log.get("event", "")
        ts_str = log.get("timestamp", "")
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except Exception:
            ts = None

        entry = dict(log)
        entry["duration_secs"] = None

        if event == "connect":
            pending[uid] = (ts, entry)
        elif event == "disconnect" and uid in pending:
            connect_ts, connect_entry = pending.pop(uid)
            if ts and connect_ts:
                connect_entry["duration_secs"] = int((ts - connect_ts).total_seconds())

        result.append(entry)

    return list(reversed(result))  # back to newest first


class SessionBarChart(QWidget):
    """Mini bar chart showing bytes transferred per recent session."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sessions = []  # list of (label, bytes_total)
        self.setMinimumHeight(90)
        self.setMaximumHeight(110)

    def set_sessions(self, sessions):
        self.sessions = sessions[-10:]  # last 10 sessions
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        pad_l, pad_r, pad_t, pad_b = 10, 10, 10, 24

        if not self.sessions:
            painter.setPen(QColor("#C4BFB8"))
            painter.drawText(self.rect(), Qt.AlignCenter, "No session data yet")
            return

        max_val = max(s[1] for s in self.sessions) or 1
        n = len(self.sessions)
        bar_w = max(8, (w - pad_l - pad_r) // n - 4)
        chart_h = h - pad_t - pad_b

        for i, (label, val) in enumerate(self.sessions):
            x = pad_l + i * ((w - pad_l - pad_r) // n)
            bar_h = max(4, int(val / max_val * chart_h))
            y = pad_t + chart_h - bar_h

            # Bar fill
            grad = QLinearGradient(x, y, x, y + bar_h)
            grad.setColorAt(0, QColor(42, 90, 255, 200))
            grad.setColorAt(1, QColor(74, 158, 110, 160))
            painter.setBrush(grad)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(x, y, bar_w, bar_h, 3, 3)

            # Label below
            painter.setPen(QColor("#9B968F"))
            painter.setFont(QFont("", 8))
            painter.drawText(x, h - pad_b + 4, bar_w, pad_b - 4,
                             Qt.AlignHCenter | Qt.AlignTop, label)


class _BandwidthCard(QWidget):
    def __init__(self, title: str, accent: QColor, direction: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.accent = accent
        self.direction = direction
        self._values = []
        self._current_mbps = 0.0
        self.setMinimumHeight(122)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def update_data(self, values):
        self._values = list(values)
        self._current_mbps = self._values[-1] if self._values else 0.0
        self.update()

    def _value_text(self):
        return _fmt_speed(self._current_mbps)

    def _build_smooth_path(self, points):
        if len(points) < 2:
            return None
        path = QPainterPath(points[0])
        for index in range(len(points) - 1):
            p0 = points[index - 1] if index > 0 else points[index]
            p1 = points[index]
            p2 = points[index + 1]
            p3 = points[index + 2] if index + 2 < len(points) else p2
            c1 = QPointF(p1.x() + (p2.x() - p0.x()) / 6.0, p1.y() + (p2.y() - p0.y()) / 6.0)
            c2 = QPointF(p2.x() - (p3.x() - p1.x()) / 6.0, p2.y() - (p3.y() - p1.y()) / 6.0)
            path.cubicTo(c1, c2, p2)
        return path

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.setPen(Qt.NoPen)

        bg = QLinearGradient(rect.topLeft(), rect.bottomRight())
        bg.setColorAt(0.0, QColor("#FFFFFF"))
        bg.setColorAt(1.0, QColor("#F7F8FA"))
        painter.setBrush(bg)
        painter.drawRoundedRect(rect, 18, 18)

        glow = QRadialGradient(rect.topRight() - QPointF(rect.width() * 0.12, -rect.height() * 0.08), rect.width() * 0.8)
        glow_color = QColor(self.accent)
        glow_color.setAlpha(18)
        glow.setColorAt(0.0, glow_color)
        glow.setColorAt(1.0, QColor(self.accent.red(), self.accent.green(), self.accent.blue(), 0))
        painter.setBrush(glow)
        glow_rect = rect.adjusted(
            int(rect.width() * 0.25),
            int(-rect.height() * 0.16),
            int(rect.width() * 0.18),
            int(rect.height() * 0.28),
        )
        painter.drawEllipse(glow_rect)

        painter.setPen(QColor(227, 231, 236))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect.adjusted(0, 0, -1, -1), 18, 18)

        # Header
        painter.setPen(QColor("#8E8E93"))
        painter.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        painter.drawText(16, 22, self.title)

        painter.setPen(QColor("#1C1C1E"))
        painter.setFont(QFont("Segoe UI", 20, QFont.Bold))
        value_rect = QRect(16, 28, rect.width() - 32, 34)
        painter.drawText(value_rect, Qt.AlignLeft | Qt.AlignVCenter, self._value_text())

        # Chart area
        chart_left = 14
        chart_top = 64
        chart_width = rect.width() - 28
        chart_height = rect.height() - chart_top - 16

        if self._values:
            peak = max(max(self._values), 1.0)
            points = []
            usable_height = max(chart_height - 8, 8)
            for index, value in enumerate(self._values):
                x = chart_left + int(index * chart_width / max(len(self._values) - 1, 1))
                y = chart_top + int(usable_height - (value / peak) * usable_height)
                points.append(QPointF(x, y))

            path = self._build_smooth_path(points)
            if path is not None:
                glow_pen = QPen(self.accent.lighter(120), 8)
                glow_pen.setCapStyle(Qt.RoundCap)
                glow_pen.setJoinStyle(Qt.RoundJoin)
                glow_pen.setColor(QColor(self.accent.red(), self.accent.green(), self.accent.blue(), 45))
                painter.setPen(glow_pen)
                painter.drawPath(path)

                core_pen = QPen(self.accent.lighter(108), 3)
                core_pen.setCapStyle(Qt.RoundCap)
                core_pen.setJoinStyle(Qt.RoundJoin)
                painter.setPen(core_pen)
                painter.drawPath(path)

        # Footer readout
        # painter.setPen(QColor("#8E8E93"))
        # painter.setFont(QFont("Segoe UI", 9, QFont.Medium))
        # arrow = '↑' if self.direction == 'up' else '↓'
        # footer = f"{arrow} {_fmt_speed(self._current_mbps)}"
        # painter.drawText(16, 20, footer)


class BandwidthGraph(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._up = []
        self._down = []
        self.setMinimumHeight(150)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.download_card = _BandwidthCard("Download", QColor("#32F5C6"), "down", self)
        self.upload_card = _BandwidthCard("Upload", QColor("#5B86FF"), "up", self)

        for card in (self.download_card, self.upload_card):
            shadow = QGraphicsDropShadowEffect(card)
            shadow.setBlurRadius(18)
            shadow.setOffset(0, 4)
            shadow.setColor(QColor(0, 0, 0, 28))
            card.setGraphicsEffect(shadow)
            layout.addWidget(card, 1)

    def update_data(self, up, down):
        self._up = list(up)
        self._down = list(down)
        self.download_card.update_data(self._down)
        self.upload_card.update_data(self._up)


class DashboardWorker(QThread):
    data_ready = pyqtSignal(list, dict)

    def __init__(self, token: str):
        super().__init__()
        self.token = token

    def _resolve_user_id(self):
        try:
            payload = json.dumps({"token": self.token}).encode()
            req = urllib.request.Request(
                f"{AUTH_API}/verify", data=payload,
                headers={"Content-Type": "application/json", "User-Agent": "MirageVPN/1.0"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as res:
                body = json.loads(res.read())
                if body.get("valid"):
                    return body.get("user_id")
        except Exception as e:
            print(f"[-] Dashboard: could not resolve user_id: {e}")
        return None

    def run(self):
        try:
            SUPABASE_URL = "https://sjbymnijaogswmysubfu.supabase.co"
            SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNqYnltbmlqYW9nc3dteXN1YmZ1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3ODc1OTkyMSwiZXhwIjoyMDk0MzM1OTIxfQ.tkwFFX3l874OtpjyIY5V5go3rMZz6X-BqO_Nl0V73I8"

            user_id = self._resolve_user_id()
            if not user_id:
                self.data_ready.emit([], {})
                return

            req = urllib.request.Request(
                f"{SUPABASE_URL}/rest/v1/connection_logs?select=*&user_id=eq.{user_id}&order=timestamp.desc&limit=200",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                }
            )
            with urllib.request.urlopen(req, timeout=10) as res:
                logs = json.loads(res.read())

            # Pair sessions for duration
            logs = pair_sessions(logs)

            # Compute stats
            connects     = [r for r in logs if r.get("event") == "connect"]
            total_sent   = sum(r.get("bytes_sent", 0)     for r in logs)
            total_recv   = sum(r.get("bytes_received", 0) for r in logs)

            durations    = [r["duration_secs"] for r in connects if r.get("duration_secs")]
            avg_duration = int(sum(durations) / len(durations)) if durations else 0

            stats = {
                "total_sent":     total_sent,
                "total_recv":     total_recv,
                "total_sessions": len(connects),
                "avg_duration":   avg_duration,
            }
            self.data_ready.emit(logs, stats)
        except Exception as e:
            print(f"[-] Dashboard fetch error: {e}")
            self.data_ready.emit([], {})


class DashboardScreen(QWidget):
    def __init__(self, token: str):
        super().__init__()
        self.token      = token
        self._all_logs  = []
        self._filter    = "all"
        self.setWindowTitle("Mirage — Dashboard")
        self.setMinimumSize(900, 640)
        self.setStyleSheet(STYLESHEET)
        self._build_ui()
        self._load_data()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#F0F2F5"))
        super().paintEvent(event)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 22)
        root.setSpacing(14)

        # ── Header ──────────────────────────────────────────────
        header = QHBoxLayout()
        title = QLabel("DASHBOARD")
        title.setObjectName("labelTitle")
        title.setStyleSheet("font-size: 20px; letter-spacing: 5px;")
        header.addWidget(title)
        header.addStretch()

        btn_refresh = QPushButton("⟳  Refresh")
        btn_refresh.setObjectName("btnGhost")
        btn_refresh.setFixedHeight(34)
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.clicked.connect(self._load_data)
        header.addWidget(btn_refresh)

        btn_export = QPushButton("↓  Export CSV")
        btn_export.setObjectName("btnGhost")
        btn_export.setFixedHeight(34)
        btn_export.setCursor(Qt.PointingHandCursor)
        btn_export.clicked.connect(self._export_csv)
        header.addWidget(btn_export)
        root.addLayout(header)

        # ── Stat cards ──────────────────────────────────────────
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        self.stat_sessions = self._stat_card("TOTAL SESSIONS", "—", "#2A5AFF")
        self.stat_sent     = self._stat_card("DATA UPLOADED",  "—", "#E87569")
        self.stat_recv     = self._stat_card("DATA DOWNLOADED","—", "#4A9E6E")
        self.stat_avg      = self._stat_card("AVG SESSION",    "—", "#C4944D")
        for card, _ in [self.stat_sessions, self.stat_sent, self.stat_recv, self.stat_avg]:
            stats_row.addWidget(card)
        root.addLayout(stats_row)

        # ── Bar chart ───────────────────────────────────────────
        chart_card = QFrame()
        chart_card.setObjectName("card")
        chart_layout = QVBoxLayout(chart_card)
        chart_layout.setContentsMargins(18, 12, 18, 10)
        chart_layout.setSpacing(6)

        chart_lbl = QLabel("DATA PER SESSION")
        chart_lbl.setObjectName("labelSection")
        chart_layout.addWidget(chart_lbl)

        self.bar_chart = SessionBarChart()
        chart_layout.addWidget(self.bar_chart)
        root.addWidget(chart_card)

        # ── Filter row ──────────────────────────────────────────
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        history_lbl = QLabel("CONNECTION HISTORY")
        history_lbl.setObjectName("labelSection")
        filter_row.addWidget(history_lbl)
        filter_row.addStretch()

        self.filter_btns = {}
        for key, label in [("all", "ALL"), ("connect", "CONNECT"), ("disconnect", "DISCONNECT")]:
            btn = QPushButton(label)
            btn.setObjectName("modeBtnActive" if key == "all" else "modeBtn")
            btn.setFixedHeight(28)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, k=key: self._set_filter(k))
            self.filter_btns[key] = btn
            filter_row.addWidget(btn)
        root.addLayout(filter_row)

        # ── Table ───────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Event", "IP Address", "Sent", "Received", "Duration", "When", "User"
        ])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.Stretch)
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background: rgba(255,255,255,0.45);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 16px;
                gridline-color: transparent;
            }
            QHeaderView::section {
                background: rgba(255,255,255,0.60);
                color: #9B968F;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 2px;
                padding: 8px 12px;
                border: none;
                border-bottom: 1px solid rgba(0,0,0,0.05);
            }
            QTableWidget::item {
                padding: 10px 12px;
                color: #3D3A36;
                font-size: 12px;
                border-bottom: 1px solid rgba(0,0,0,0.03);
            }
            QTableWidget::item:selected {
                background: rgba(42, 90, 255, 0.08);
                color: #2A5AFF;
            }
            QTableWidget::item:alternate {
                background: rgba(0,0,0,0.015);
            }
        """)
        root.addWidget(self.table)

        self.status_label = QLabel("Loading...")
        self.status_label.setObjectName("labelFieldName")
        self.status_label.setAlignment(Qt.AlignCenter)
        root.addWidget(self.status_label)

    def _stat_card(self, title, value, accent="#2A5AFF"):
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(4)

        t = QLabel(title)
        t.setObjectName("labelFieldName")
        t.setAlignment(Qt.AlignCenter)

        v = QLabel(value)
        v.setObjectName("labelFieldValue")
        v.setAlignment(Qt.AlignCenter)
        v.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {accent};")

        layout.addWidget(t)
        layout.addWidget(v)
        return card, v

    def _set_filter(self, key: str):
        self._filter = key
        for k, btn in self.filter_btns.items():
            btn.setObjectName("modeBtnActive" if k == key else "modeBtn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._populate_table(self._all_logs)

    def _load_data(self):
        self.status_label.setText("Loading...")
        self.worker = DashboardWorker(self.token)
        self.worker.data_ready.connect(self._on_data)
        self.worker.start()

    def _on_data(self, logs, stats):
        self._all_logs = logs

        # Stat cards
        self.stat_sessions[1].setText(str(stats.get("total_sessions", 0)))
        self.stat_sent[1].setText(format_bytes(stats.get("total_sent", 0)))
        self.stat_recv[1].setText(format_bytes(stats.get("total_recv", 0)))

        avg = stats.get("avg_duration", 0)
        if avg >= 3600:
            avg_str = f"{avg//3600}h {(avg%3600)//60}m"
        elif avg >= 60:
            avg_str = f"{avg//60}m {avg%60}s"
        else:
            avg_str = f"{avg}s" if avg else "—"
        self.stat_avg[1].setText(avg_str)

        # Bar chart — sessions with bytes data
        sessions = []
        for log in reversed(logs):
            if log.get("event") == "connect":
                total = (log.get("bytes_sent", 0) or 0) + (log.get("bytes_received", 0) or 0)
                ts = log.get("timestamp", "")
                label = ts[11:16] if len(ts) >= 16 else "—"
                sessions.append((label, total))
        self.bar_chart.set_sessions(sessions)

        self._populate_table(logs)

    def _populate_table(self, logs):
        filtered = logs
        if self._filter != "all":
            filtered = [r for r in logs if r.get("event") == self._filter]

        self.table.setRowCount(len(filtered))
        self._logs = filtered

        for row, log in enumerate(filtered):
            event    = log.get("event", "")
            is_conn  = event == "connect"
            color    = QColor(74, 158, 110) if is_conn else QColor(196, 86, 77)
            bg_color = QColor(74, 158, 110, 12) if is_conn else QColor(196, 86, 77, 12)

            # Duration
            dur_secs = log.get("duration_secs")
            if dur_secs is not None:
                if dur_secs >= 3600:
                    dur = f"{dur_secs//3600}h {(dur_secs%3600)//60}m"
                elif dur_secs >= 60:
                    dur = f"{dur_secs//60}m {dur_secs%60}s"
                else:
                    dur = f"{dur_secs}s"
            else:
                dur = "—"

            cells = [
                ("● " + event.upper(), color, True),
                (log.get("ip_address", ""),         QColor("#3D3A36"), False),
                (format_bytes(log.get("bytes_sent", 0)),      QColor("#E87569"), False),
                (format_bytes(log.get("bytes_received", 0)),  QColor("#4A9E6E"), False),
                (dur,                                QColor("#C4944D"), False),
                (relative_time(log.get("timestamp", "")),     QColor("#9B968F"), False),
                (str(log.get("user_id", ""))[:8] + "…",       QColor("#B0ACA6"), False),
            ]

            for col, (text, fg, bold) in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setForeground(fg)
                if bold:
                    item.setFont(QFont("", -1, QFont.Bold))
                item.setBackground(bg_color)
                self.table.setItem(row, col, item)

            self.table.setRowHeight(row, 40)

        self.status_label.setText(
            f"{len(filtered)} records" +
            (f" (filtered from {len(logs)})" if self._filter != "all" else "")
        )

    def _export_csv(self):
        if not hasattr(self, "_logs") or not self._logs:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", "mirage_logs.csv", "CSV Files (*.csv)"
        )
        if not path:
            return
        try:
            import csv
            with open(path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "event", "ip_address", "bytes_sent",
                    "bytes_received", "duration_secs", "timestamp", "user_id"
                ])
                writer.writeheader()
                writer.writerows(self._logs)
        except Exception as e:
            print(f"[-] Export error: {e}")


class MirageApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mirage VPN")
        self.setMinimumSize(540, 900)
        self.setStyleSheet(STYLESHEET)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setMouseTracking(True)
        # Use application-level filter to catch events from all children
        QCoreApplication.instance().installEventFilter(self)
        self._drag_pos = None
        self._resize_dir = None
        self._dragging = False
        self._resizing = False

        # Restore firewall on any exit
        atexit.register(self._emergency_restore)

        # Handle CTRL+C and system signals
        signal.signal(signal.SIGTERM, self._signal_handler)
        if platform.system() != "Windows":
            signal.signal(signal.SIGHUP, self._signal_handler)

        # Ensure system-start safety net exists (best effort)
        self._ensure_startup_restore_task()

        self._check_auto_login()

    def _check_auto_login(self):
        settings = QSettings("Mirage", "MirageVPN")
        token = settings.value("auth_token")
        user = settings.value("auth_user")
        remember = settings.value("remember_me", False, type=bool)
        
        if remember and token and user:
            self._on_login(token, user)
        else:
            self._show_login()

    def _build_title_bar(self, show_logout=False):
        bar = QWidget()
        bar.setObjectName("titleBar")
        bar.setFixedHeight(44)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 10, 14, 6)
        layout.setSpacing(6)

        # Traffic light buttons
        btn_close = QPushButton()
        btn_close.setObjectName("trafficBtn")
        btn_close.setStyleSheet("background: #FF5F57;")
        btn_close.setFixedSize(14, 14)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

        btn_min = QPushButton()
        btn_min.setObjectName("trafficBtn")
        btn_min.setStyleSheet("background: #FEBC2E;")
        btn_min.setFixedSize(14, 14)
        btn_min.setCursor(Qt.PointingHandCursor)
        btn_min.clicked.connect(self.showMinimized)
        layout.addWidget(btn_min)

        btn_max = QPushButton()
        btn_max.setFixedSize(14, 14)
        btn_max.setObjectName("trafficBtn")
        btn_max.setStyleSheet("background: #28C840;")
        layout.addWidget(btn_max)

        layout.addStretch()

        if show_logout:
            btn_logout = QPushButton("LOGOUT")
            btn_logout.setObjectName("btnLogout")
            btn_logout.setCursor(Qt.PointingHandCursor)
            btn_logout.clicked.connect(self._show_login)
            layout.addWidget(btn_logout)

        # IP label (removed, relocated to main screen)

        return bar

    def _get_resize_dir(self, pos):
        m = 10
        w, h = self.width(), self.height()
        x, y = pos.x(), pos.y()
        l, r, t, b = x < m, x > w - m, y < m, y > h - m
        if l and t: return "tl"
        if r and t: return "tr"
        if l and b: return "bl"
        if r and b: return "br"
        if l: return "l"
        if r: return "r"
        if t: return "t"
        if b: return "b"
        return None

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseMove and not self._dragging and not self._resizing:
            pos = self.mapFromGlobal(QCursor.pos()) # global to local
            dir = self._get_resize_dir(pos)
            if dir in ["tl", "br"]: self.setCursor(Qt.SizeFDiagCursor)
            elif dir in ["tr", "bl"]: self.setCursor(Qt.SizeBDiagCursor)
            elif dir in ["l", "r"]: self.setCursor(Qt.SizeHorCursor)
            elif dir in ["t", "b"]: self.setCursor(Qt.SizeVerCursor)
            else: self.setCursor(Qt.ArrowCursor)
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._resize_dir = self._get_resize_dir(event.pos())
            if self._resize_dir:
                self._resizing = True
                self._start_geom = self.geometry()
                self._start_pos  = event.globalPos()
            elif event.pos().y() < 60:
                self._dragging = True
                self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._resizing:
            delta = event.globalPos() - self._start_pos
            g = QRect(self._start_geom)
            min_w, min_h = self.minimumSize().width(), self.minimumSize().height()
            
            if "l" in self._resize_dir: 
                new_w = max(min_w, g.width() - delta.x())
                g.setLeft(g.right() - new_w)
            if "r" in self._resize_dir: 
                g.setRight(max(g.left() + min_w, g.right() + delta.x()))
            if "t" in self._resize_dir: 
                new_h = max(min_h, g.height() - delta.y())
                g.setTop(g.bottom() - new_h)
            if "b" in self._resize_dir: 
                g.setBottom(max(g.top() + min_h, g.bottom() + delta.y()))
            
            self.setGeometry(g)
            event.accept()
            return

        if self._dragging:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()
            return

        # Update cursor shape on hover
        dir = self._get_resize_dir(event.pos())
        if dir in ["tl", "br"]: self.setCursor(Qt.SizeFDiagCursor)
        elif dir in ["tr", "bl"]: self.setCursor(Qt.SizeBDiagCursor)
        elif dir in ["l", "r"]: self.setCursor(Qt.SizeHorCursor)
        elif dir in ["t", "b"]: self.setCursor(Qt.SizeVerCursor)
        else: self.setCursor(Qt.ArrowCursor)

    def mouseReleaseEvent(self, event):
        self._dragging = False
        self._resizing = False
        self._resize_dir = None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        path = QPainterPath()
        # 16px radius is safer for button visibility
        path.addRoundedRect(QRectF(self.rect()), 16, 16)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def _ensure_startup_restore_task(self):
        """Create/update a startup task that restores default firewall policy."""
        if platform.system() == "Windows":
            restore_cmd = (
                "cmd /c netsh advfirewall set allprofiles "
                "firewallpolicy blockinbound,allowoutbound"
            )
            subprocess.run(
                [
                    'schtasks', '/Create', '/TN', 'MirageFirewallRestore',
                    '/SC', 'ONSTART', '/RL', 'HIGHEST', '/F', '/TR', restore_cmd
                ],
                capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
            )

    def _emergency_restore(self):
        """Last resort \u2014 restore firewall on any exit."""
        if platform.system() == "Windows":
            subprocess.run(
                ['netsh', 'advfirewall', 'set', 'allprofiles',
                 'firewallpolicy', 'blockinbound,allowoutbound'],
                capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
        if os.path.exists("ks_active.flag"):
            os.remove("ks_active.flag")

    def _signal_handler(self, sig, frame):
        self._emergency_restore()
        sys.exit(0)

    def closeEvent(self, event):
        """Called when X button clicked \u2014 restore firewall before closing."""
        self._emergency_restore()
        # Disconnect VPN if connected
        screen = self.centralWidget()
        if isinstance(screen, QWidget):
            inner = screen.findChild(MainScreen)
            if inner and inner.connected:
                inner._disconnect()
            elif isinstance(screen, MainScreen) and screen.connected:
                screen._disconnect()
        event.accept()

    def _show_login(self):
        # Explicitly clear saved session on logout/manual login show
        settings = QSettings("Mirage", "MirageVPN")
        settings.remove("auth_token")
        settings.remove("auth_user")
        settings.setValue("remember_me", False)

        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(0)
        wrapper_layout.addWidget(self._build_title_bar())

        screen = LoginScreen()
        screen.login_success.connect(self._on_login)
        wrapper_layout.addWidget(screen)

        self.setCentralWidget(wrapper)
        # self.resize(540, 900)
        self._center()
    
    def _on_login(self, token: str, username: str):
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(0)
        wrapper_layout.addWidget(self._build_title_bar(show_logout=True))

        screen = MainScreen(token, username)
        screen.logout_requested.connect(self._show_login)
        wrapper_layout.addWidget(screen)

        self.setCentralWidget(wrapper)
        # self.resize(540, 900)
        self._center()

    def _center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())


def _ensure_admin():
    import ctypes, sys
    if not ctypes.windll.shell32.IsUserAnAdmin():
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit(0)


def main():
    _ensure_admin()
    app = QApplication(sys.argv)
    app.setApplicationName("Mirage VPN")
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#F0F2F5"))
    palette.setColor(QPalette.WindowText, QColor("#1C1C1E"))
    palette.setColor(QPalette.Base, QColor("#FFFFFF"))
    palette.setColor(QPalette.AlternateBase, QColor("#F8F9FA"))
    palette.setColor(QPalette.Text, QColor("#1C1C1E"))
    palette.setColor(QPalette.Button, QColor("#FFFFFF"))
    palette.setColor(QPalette.ButtonText, QColor("#1C1C1E"))
    palette.setColor(QPalette.Highlight, QColor("#0066FF"))
    palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(palette)

    window = MirageApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()