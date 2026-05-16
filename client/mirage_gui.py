import sys
import os
import atexit
import signal
import socket
import threading
import json
import time
import re
import subprocess
import platform
import urllib.request
import urllib.error
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtCore import QMetaObject, Q_ARG, pyqtSlot

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


# -- STYLESHEET --------------------------------------------------------------
STYLESHEET = """
QWidget {
    background-color: transparent;
    color: #3D3A36;
    font-family: 'Inter', 'Montserrat', 'Segoe UI', sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #EDE9E3;
}

#titleBar {
    background: transparent;
}
#titleBar QToolButton {
    background: rgba(255,255,255,0.45);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 11px;
    min-width: 22px; min-height: 22px;
    font-size: 11px;
    color: #7A756E;
}
#titleBar QToolButton:hover {
    background: rgba(255,255,255,0.70);
}
#titleBar QLabel {
    color: #8A857E;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 3px;
}

#card {
    background-color: rgba(255, 255, 255, 0.50);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 24px;
}

#actionHub {
    background-color: rgba(255, 255, 255, 0.55);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 26px;
}

#serverPill {
    background-color: rgba(255, 255, 255, 0.40);
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 20px;
}

#bottomDock {
    background-color: rgba(255, 255, 255, 0.45);
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 22px;
}

QLabel#labelTitle {
    color: #2E2B27;
    font-size: 28px;
    font-weight: 800;
    letter-spacing: 4px;
}
QLabel#labelSubtitle {
    color: #8A857E;
    font-size: 12px;
    letter-spacing: 2px;
}
QLabel#labelStatus {
    color: #C4564D;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 3px;
}
QLabel#labelStatusConnected {
    color: #4A9E6E;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 3px;
}
QLabel#labelStatusConnecting {
    color: #C4944D;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 3px;
}
QLabel#labelFieldName {
    color: #9B968F;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 2px;
}
QLabel#labelFieldValue {
    color: #3D3A36;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.5px;
}
QLabel#labelUsername {
    color: #7A756E;
    font-size: 12px;
    font-weight: 600;
}
QLabel#labelSection {
    color: #9B968F;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 3px;
}

QFrame#divider {
    background-color: rgba(0, 0, 0, 0.06);
    border: none;
    max-height: 1px;
}

QLineEdit {
    background-color: rgba(255, 255, 255, 0.35);
    border: 1px solid rgba(0, 0, 0, 0.05);
    border-radius: 14px;
    padding: 13px 18px;
    color: #2E2B27;
    font-size: 13px;
    letter-spacing: 0.5px;
    selection-background-color: rgba(42, 90, 255, 0.15);
}
QLineEdit:focus {
    border: 1px solid rgba(42, 90, 255, 0.30);
    background-color: rgba(255, 255, 255, 0.55);
}
QLineEdit::placeholder {
    color: #B0ACA6;
}

QPushButton#btnPrimary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #2A5AFF, stop:1 #4A7AFF);
    color: white;
    border: 1px solid rgba(42, 90, 255, 0.30);
    border-radius: 14px;
    padding: 13px 24px;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 2px;
}
QPushButton#btnPrimary:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #3566FF, stop:1 #5A88FF);
}
QPushButton#btnPrimary:pressed {
    background: #2450DD;
}
QPushButton#btnPrimary:disabled {
    background: rgba(180, 175, 168, 0.40);
    color: #9B968F;
    border: 1px solid rgba(0, 0, 0, 0.04);
}

QPushButton#btnGhost {
    background: rgba(255, 255, 255, 0.40);
    color: #5C5854;
    border: 1px solid rgba(0, 0, 0, 0.05);
    border-radius: 12px;
    padding: 10px 16px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 1px;
}
QPushButton#btnGhost:hover {
    background: rgba(255, 255, 255, 0.65);
    border: 1px solid rgba(0, 0, 0, 0.08);
}
QPushButton#btnGhost:pressed {
    background: rgba(255, 255, 255, 0.30);
}

QPushButton#btnDanger {
    background: rgba(196, 86, 77, 0.08);
    color: #C4564D;
    border: 1px solid rgba(196, 86, 77, 0.12);
    border-radius: 12px;
    padding: 10px 16px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#btnDanger:hover {
    background: rgba(196, 86, 77, 0.14);
}

QPushButton#btnConnect {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #2A5AFF, stop:1 #4A7AFF);
    color: white;
    border: 1px solid rgba(42, 90, 255, 0.25);
    border-radius: 18px;
    padding: 11px 24px;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 2px;
}
QPushButton#btnConnect:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #3566FF, stop:1 #5A88FF);
}
QPushButton#btnConnect:pressed {
    background: #2450DD;
}

QPushButton#btnConnectActive {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #3A9E6E, stop:1 #50B882);
    color: white;
    border: 1px solid rgba(58, 158, 110, 0.25);
    border-radius: 18px;
    padding: 11px 24px;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 2px;
}
QPushButton#btnConnectActive:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #45A878, stop:1 #5CC28C);
}

QCheckBox#toggle {
    spacing: 8px;
    color: #7A756E;
    font-size: 12px;
    letter-spacing: 1px;
}
QCheckBox#toggle::indicator {
    width: 40px;
    height: 22px;
    border-radius: 12px;
    background-color: rgba(0, 0, 0, 0.08);
    border: 1px solid rgba(0, 0, 0, 0.05);
}
QCheckBox#toggle::indicator:checked {
    background-color: #2A5AFF;
    border: 1px solid rgba(42, 90, 255, 0.30);
}
QCheckBox#toggle::indicator:unchecked:hover {
    background-color: rgba(0, 0, 0, 0.12);
}

QLabel#labelError {
    color: #A63D35;
    font-size: 11px;
    background: rgba(196, 86, 77, 0.08);
    border: 1px solid rgba(196, 86, 77, 0.15);
    border-radius: 10px;
    padding: 8px 14px;
    letter-spacing: 0.5px;
}
QLabel#labelSuccess {
    color: #3A8E5E;
    font-size: 11px;
    background: rgba(74, 158, 110, 0.08);
    border: 1px solid rgba(74, 158, 110, 0.15);
    border-radius: 10px;
    padding: 8px 14px;
    letter-spacing: 0.5px;
}

QScrollBar:vertical {
    background: rgba(0, 0, 0, 0.03);
    width: 5px;
    border-radius: 2px;
}
QScrollBar::handle:vertical {
    background: rgba(0, 0, 0, 0.10);
    border-radius: 2px;
}

QTabWidget::pane {
    border: none;
    background: transparent;
}
QTabBar::tab {
    background: transparent;
    color: #9B968F;
    padding: 8px 20px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 2px;
    border-bottom: 2px solid transparent;
}
QTabBar::tab:selected {
    color: #2A5AFF;
    border-bottom: 2px solid #2A5AFF;
}
QTabBar::tab:hover {
    color: #6A665F;
}

QPushButton#modeBtn,
QPushButton#modeBtnActive {
    border-radius: 12px;
    padding: 9px 14px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 2px;
}
QPushButton#modeBtn {
    background: rgba(255, 255, 255, 0.30);
    color: #9B968F;
    border: 1px solid rgba(0, 0, 0, 0.04);
}
QPushButton#modeBtnActive {
    background: rgba(255, 255, 255, 0.60);
    color: #2A5AFF;
    border: 1px solid rgba(42, 90, 255, 0.12);
}

QToolButton#iconBtn,
QToolButton#dockBtn {
    background: rgba(255, 255, 255, 0.40);
    color: #7A756E;
    border: 1px solid rgba(0, 0, 0, 0.04);
    border-radius: 14px;
    font-size: 13px;
    font-weight: 600;
}
QToolButton#iconBtn {
    min-width: 34px;
    min-height: 34px;
}
QToolButton#dockBtn {
    min-width: 44px;
    min-height: 36px;
}
QToolButton#iconBtn:hover,
QToolButton#dockBtn:hover {
    background: rgba(255, 255, 255, 0.65);
    border: 1px solid rgba(0, 0, 0, 0.06);
}
QToolButton#dockBtn:checked {
    background: rgba(42, 90, 255, 0.10);
    color: #2A5AFF;
    border: 1px solid rgba(42, 90, 255, 0.12);
}

#heroPanel {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(240, 210, 190, 0.60), stop:1 rgba(210, 200, 230, 0.50));
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 20px 0px 0px 20px;
}
QLabel#heroTitle {
    color: #3D3A36;
    font-size: 32px;
    font-weight: 800;
    letter-spacing: 6px;
}
QLabel#heroSubtitle {
    color: #7A756E;
    font-size: 13px;
    letter-spacing: 1px;
    font-weight: 500;
}
QLabel#heroBadge {
    color: #5C5854;
    font-size: 11px;
    letter-spacing: 1px;
    font-weight: 600;
    padding: 6px 14px;
    background: rgba(255, 255, 255, 0.35);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 10px;
}

#loginShell {
    background: rgba(255, 255, 255, 0.45);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 20px;
}
"""
# ---------------------------------------------------------------------------


class VPNWorker(QThread):
    """Background thread — manages VPN tunnel connection."""
    status_changed   = pyqtSignal(str)   # "connecting" | "connected" | "disconnected" | "error"
    bytes_updated    = pyqtSignal(int, int)  # sent, received
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


class AuthWorker(QThread):
    """Background thread — handles login/register API calls."""
    finished = pyqtSignal(bool, str, str)  # success, token/error, username

    def __init__(self, action: str, username: str, password: str, email: str = ""):
        super().__init__()
        self.action   = action
        self.username = username
        self.password = password
        self.email    = email

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
                    self.finished.emit(True, body.get("token", ""), body.get("username", self.username))
                else:
                    self.finished.emit(True, "", self.email)
        except urllib.error.HTTPError as e:
            try:
                body = json.loads(e.read())
                if body.get("requires_verification"):
                    self.finished.emit(False, "requires_verification:" + body.get("email", ""), "")
                else:
                    self.finished.emit(False, body.get("error", "Request failed"), "")
            except Exception:
                self.finished.emit(False, "Request failed", "")
        except Exception as e:
            self.finished.emit(False, str(e), "")


class OTPWorker(QThread):
    """Background thread — handles email OTP validation and resending."""
    finished = pyqtSignal(bool, str)  # success, message/error

    def __init__(self, action: str, email: str, code: str = ""):
        super().__init__()
        self.action = action
        self.email  = email
        self.code   = code

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
                self.finished.emit(True, body.get("message", "Success"))
        except urllib.error.HTTPError as e:
            try:
                body = json.loads(e.read())
                self.finished.emit(False, body.get("error", "Request failed"))
            except Exception:
                self.finished.emit(False, "Request failed")
        except Exception as e:
            self.finished.emit(False, str(e))


def format_bytes(b: int) -> str:
    if b < 1024:
        return f"{b} B"
    elif b < 1024 ** 2:
        return f"{b/1024:.1f} KB"
    else:
        return f"{b/1024**2:.2f} MB"


class IPLookupWorker(QThread):
    """Background thread — fetches public IP and geo-location."""
    result = pyqtSignal(str, str)  # ip, location

    def run(self):
        try:
            req = urllib.request.Request(
                "http://ip-api.com/json/?fields=query,city,country",
                headers={"User-Agent": "MirageVPN/1.0"}
            )
            with urllib.request.urlopen(req, timeout=6) as res:
                data = json.loads(res.read())
                ip = data.get("query", "0.0.0.0")
                city = data.get("city", "")
                country = data.get("country", "")
                loc = f"{city}, {country}" if city else country or "Unknown"
                self.result.emit(ip, loc)
        except Exception:
            self.result.emit("0.0.0.0", "Unknown")


class MapRadarWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(240)
        self._pulse = 0.0
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._tick)
        self._pulse_timer.start(42)

    def _tick(self):
        self._pulse = (self._pulse + 0.02) % 1.0
        self.update()

    def _inside_land(self, nx: float, ny: float) -> bool:
        # Ellipse clusters provide a light, abstract world-map silhouette.
        shapes = [
            (0.22, 0.45, 0.14, 0.10),
            (0.34, 0.44, 0.10, 0.08),
            (0.48, 0.43, 0.09, 0.07),
            (0.59, 0.40, 0.12, 0.09),
            (0.69, 0.45, 0.11, 0.08),
            (0.79, 0.42, 0.09, 0.07),
            (0.56, 0.58, 0.09, 0.10),
        ]
        for cx, cy, rx, ry in shapes:
            if ((nx - cx) / rx) ** 2 + ((ny - cy) / ry) ** 2 <= 1.0:
                return True
        return False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        w = self.width()
        h = self.height()

        spacing = 10
        r = 1.8
        for y in range(10, h - 10, spacing):
            for x in range(10, w - 10, spacing):
                nx = x / max(1, w)
                ny = y / max(1, h)
                if self._inside_land(nx, ny):
                    painter.setBrush(QColor(190, 182, 172, 200))
                else:
                    painter.setBrush(QColor(210, 204, 196, 90))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(QPointF(x, y), r, r)

        center = QPointF(w * 0.56, h * 0.46)
        base_radius = 10
        painter.setBrush(QColor(232, 117, 106, 180))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(center, base_radius, base_radius)

        for offset in [0.0, 0.35, 0.7]:
            phase = (self._pulse + offset) % 1.0
            radius = 12 + phase * 50
            alpha = max(0, int(120 * (1.0 - phase)))
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor(232, 117, 106, alpha), 1.5))
            painter.drawEllipse(center, radius, radius)


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
        shell_layout = QHBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        hero = QFrame()
        hero.setObjectName("heroPanel")
        hero.setMinimumWidth(300)
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(34, 34, 34, 34)
        hero_layout.setSpacing(14)

        brand = QLabel("MIRAGE")
        brand.setObjectName("heroTitle")
        hero_layout.addWidget(brand)

        tagline = QLabel("Network privacy with a ruthless edge.")
        tagline.setObjectName("heroSubtitle")
        tagline.setWordWrap(True)
        hero_layout.addWidget(tagline)

        hero_layout.addSpacing(12)
        for label in [
            "AES-256 encrypted tunnel",
            "Kill switch fail-safe",
            "High anonymity routing",
        ]:
            badge = QLabel(label)
            badge.setObjectName("heroBadge")
            hero_layout.addWidget(badge, 0, Qt.AlignLeft)
        hero_layout.addStretch()

        form_host = QFrame()
        form_layout = QVBoxLayout(form_host)
        form_layout.setContentsMargins(34, 34, 34, 34)
        form_layout.setSpacing(12)

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
        lt.setSpacing(12)

        self.login_user = QLineEdit()
        self.login_user.setPlaceholderText("Username or email")
        lt.addWidget(self.login_user)

        self.login_pass = QLineEdit()
        self.login_pass.setPlaceholderText("Password")
        self.login_pass.setEchoMode(QLineEdit.Password)
        self._attach_password_toggle(self.login_pass)
        lt.addWidget(self.login_pass)

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

        shell_layout.addWidget(hero, 4)
        shell_layout.addWidget(form_host, 6)
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
            btn.setText("PLEASE WAIT...")
        else:
            btn.setText("SIGN IN" if btn == self.btn_login else "CREATE ACCOUNT")

    def _do_login(self):
        u = self.login_user.text().strip()
        p = self.login_pass.text()
        if not u or not p:
            self._show_error(self.login_msg, "Please fill all fields.")
            return
        self._set_loading(self.btn_login, True)
        self.login_msg.hide()
        self.auth_worker = AuthWorker("login", u, p)
        self.auth_worker.finished.connect(self._on_login_done)
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
        self._set_loading(self.btn_register, True)
        self.reg_msg.hide()
        self.auth_worker = AuthWorker("register", u, p, e)
        self.auth_worker.finished.connect(self._on_register_done)
        self.auth_worker.start()

    def _on_login_done(self, success, token, username):
        self._set_loading(self.btn_login, False)
        if success:
            self.login_success.emit(token, username)
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
        self.otp_worker.finished.connect(self._on_verify_done)
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
        self.otp_worker.finished.connect(self._on_resend_done)
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
        self._connect_anim_step = 0
        self._last_bytes_time = None
        self._last_sent = 0
        self._last_recv = 0
        self._build_ui()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), QColor("#EDE9E3"))

        blobs = [
            (QPointF(self.width() * 0.15, self.height() * 0.22), QColor(245, 213, 192, 110), 420),
            (QPointF(self.width() * 0.85, self.height() * 0.16), QColor(200, 223, 198, 95), 380),
            (QPointF(self.width() * 0.50, self.height() * 0.88), QColor(212, 201, 232, 100), 450),
            (QPointF(self.width() * 0.70, self.height() * 0.55), QColor(240, 220, 200, 60), 300),
        ]

        for center, color, radius in blobs:
            grad = QRadialGradient(center, radius)
            grad.setColorAt(0.0, color)
            grad.setColorAt(0.5, QColor(color.red(), color.green(), color.blue(), color.alpha() // 2))
            grad.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 0))
            painter.setBrush(grad)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(center, radius, radius)

        super().paintEvent(event)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 24, 32, 24)
        root.setSpacing(16)

        header = QHBoxLayout()
        self.btn_profile = QToolButton()
        self.btn_profile.setObjectName("iconBtn")
        self.btn_profile.setText("\u2630")
        self.btn_profile.setToolTip("Profile")
        header.addWidget(self.btn_profile)

        header.addStretch()

        title = QLabel("MIRAGE")
        title.setObjectName("labelTitle")
        title.setStyleSheet("font-size: 22px; letter-spacing: 6px; font-weight: 800;")
        header.addWidget(title)

        header.addStretch()

        self.btn_settings = QToolButton()
        self.btn_settings.setObjectName("iconBtn")
        self.btn_settings.setText("\u2699")
        self.btn_settings.setToolTip("Settings")
        header.addWidget(self.btn_settings)

        self.btn_info = QToolButton()
        self.btn_info.setObjectName("iconBtn")
        self.btn_info.setText("\u2139")
        self.btn_info.setToolTip("Info")
        header.addWidget(self.btn_info)

        root.addLayout(header)

        self.map_card = QFrame()
        self.map_card.setObjectName("card")
        map_layout = QVBoxLayout(self.map_card)
        map_layout.setContentsMargins(22, 16, 22, 14)
        map_layout.setSpacing(8)

        self.status_label = QLabel("DISCONNECTED")
        self.status_label.setObjectName("labelStatus")
        self.status_label.setAlignment(Qt.AlignCenter)
        map_layout.addWidget(self.status_label)

        self.map_widget = MapRadarWidget()
        map_layout.addWidget(self.map_widget)
        root.addWidget(self.map_card)

        action_hub = QFrame()
        action_hub.setObjectName("actionHub")
        action_layout = QHBoxLayout(action_hub)
        action_layout.setContentsMargins(14, 12, 14, 12)
        action_layout.setSpacing(10)

        self.btn_refresh = QToolButton()
        self.btn_refresh.setObjectName("iconBtn")
        self.btn_refresh.setText("\u27F3")
        self.btn_refresh.setToolTip("Refresh server")
        action_layout.addWidget(self.btn_refresh)

        server_pill = QFrame()
        server_pill.setObjectName("serverPill")
        server_layout = QHBoxLayout(server_pill)
        server_layout.setContentsMargins(14, 10, 14, 10)
        server_layout.setSpacing(10)

        self.server_label = QLabel("Stockholm, SE")
        self.server_label.setObjectName("labelFieldValue")
        server_layout.addWidget(self.server_label)

        self.signal_label = QLabel("Signal: Strong")
        self.signal_label.setObjectName("labelFieldName")
        server_layout.addWidget(self.signal_label)

        server_layout.addStretch()

        self.btn_connect = QPushButton("CONNECT")
        self.btn_connect.setObjectName("btnConnect")
        self.btn_connect.setCursor(Qt.PointingHandCursor)
        self.btn_connect.setMinimumWidth(140)
        self.btn_connect.setFixedHeight(42)
        self.btn_connect.clicked.connect(self._toggle_connection)
        self.btn_connect.setToolTip("Connect or disconnect VPN")

        self.btn_connect_glow = QGraphicsDropShadowEffect(self.btn_connect)
        self.btn_connect_glow.setOffset(0, 4)
        self.btn_connect_glow.setColor(QColor(42, 90, 255, 90))
        self.btn_connect_glow.setBlurRadius(28)
        self.btn_connect.setGraphicsEffect(self.btn_connect_glow)

        server_layout.addWidget(self.btn_connect)
        action_layout.addWidget(server_pill, 1)

        self.btn_lookup = QToolButton()
        self.btn_lookup.setObjectName("iconBtn")
        self.btn_lookup.setText("\u25CE")
        self.btn_lookup.setToolTip("Lookup location")
        action_layout.addWidget(self.btn_lookup)

        root.addWidget(action_hub)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(0)

        stats_row.addStretch()

        self.lbl_ip = QLabel("IP: ...")
        self.lbl_ip.setObjectName("labelFieldValue")
        self.lbl_ip.setAlignment(Qt.AlignCenter)
        stats_row.addWidget(self.lbl_ip)

        spacer1 = QLabel("·")
        spacer1.setObjectName("labelFieldName")
        spacer1.setStyleSheet("color: #C4BFB8; font-size: 16px; padding: 0 14px;")
        stats_row.addWidget(spacer1)

        self.lbl_location = QLabel("Location: ...")
        self.lbl_location.setObjectName("labelFieldValue")
        self.lbl_location.setAlignment(Qt.AlignCenter)
        stats_row.addWidget(self.lbl_location)

        spacer2 = QLabel("·")
        spacer2.setObjectName("labelFieldName")
        spacer2.setStyleSheet("color: #C4BFB8; font-size: 16px; padding: 0 14px;")
        stats_row.addWidget(spacer2)

        self.lbl_duration = QLabel("Duration: 00:00")
        self.lbl_duration.setObjectName("labelFieldValue")
        self.lbl_duration.setAlignment(Qt.AlignCenter)
        stats_row.addWidget(self.lbl_duration)

        stats_row.addStretch()

        root.addLayout(stats_row)

        self.rate_label = QLabel("UP 0 B/s | DOWN 0 B/s")
        self.rate_label.setObjectName("labelFieldName")
        self.rate_label.setAlignment(Qt.AlignCenter)
        root.addWidget(self.rate_label)

        dock = QFrame()
        dock.setObjectName("bottomDock")
        dock_layout = QHBoxLayout(dock)
        dock_layout.setContentsMargins(16, 10, 16, 10)
        dock_layout.setSpacing(10)
        dock_layout.addStretch()

        self.dock_home = QToolButton()
        self.dock_home.setObjectName("dockBtn")
        self.dock_home.setText("\u25C9")
        dock_layout.addWidget(self.dock_home)

        self.btn_dashboard = QToolButton()
        self.btn_dashboard.setObjectName("dockBtn")
        self.btn_dashboard.setText("📊")
        self.btn_dashboard.setToolTip("Dashboard")
        self.btn_dashboard.setCursor(Qt.PointingHandCursor)
        self.btn_dashboard.clicked.connect(self._open_dashboard)
        dock_layout.addWidget(self.btn_dashboard)

        self.toggle_ks = QCheckBox("KS")
        self.toggle_ks.setObjectName("toggle")
        self.toggle_ks.setCursor(Qt.PointingHandCursor)
        self.toggle_ks.setToolTip("Kill switch")
        self.toggle_ks.toggled.connect(self._on_ks_toggled)
        dock_layout.addWidget(self.toggle_ks)

        self.toggle_anon = QCheckBox("ANON")
        self.toggle_anon.setObjectName("toggle")
        self.toggle_anon.setCursor(Qt.PointingHandCursor)
        self.toggle_anon.setToolTip("High anonymity")
        self.toggle_anon.toggled.connect(self._on_anon_toggled)
        dock_layout.addWidget(self.toggle_anon)

        self.dock_power = QToolButton()
        self.dock_power.setObjectName("dockBtn")
        self.dock_power.setText("\u26A1")
        dock_layout.addWidget(self.dock_power)

        self.btn_logout = QPushButton("Sign Out")
        self.btn_logout.setObjectName("btnGhost")
        self.btn_logout.setFixedHeight(34)
        self.btn_logout.setCursor(Qt.PointingHandCursor)
        self.btn_logout.clicked.connect(self._do_logout)
        dock_layout.addWidget(self.btn_logout)

        dock_layout.addStretch()
        root.addWidget(dock)

        self.error_label = QLabel("")
        self.error_label.setObjectName("labelError")
        self.error_label.hide()
        root.addWidget(self.error_label)

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

        # Fetch real IP and location
        self._ip_worker = IPLookupWorker()
        self._ip_worker.result.connect(self._on_ip_result)
        self._ip_worker.start()

    def _on_ip_result(self, ip: str, location: str):
        self.lbl_ip.setText(f"IP: {ip}")
        self.lbl_location.setText(f"Location: {location}")

    def _refresh_ip(self):
        """Re-fetch public IP and location."""
        self.lbl_ip.setText("IP: ...")
        self.lbl_location.setText("Location: ...")
        self._ip_worker = IPLookupWorker()
        self._ip_worker.result.connect(self._on_ip_result)
        self._ip_worker.start()

    def _toggle_connection(self):
        if not self.connected:
            self._connect()
        else:
            self._disconnect()

    def _connect(self):
        self.btn_connect.setEnabled(False)
        self.status_label.setObjectName("labelStatusConnecting")
        self.status_label.setText("CONNECTING...")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        self._connect_anim_step = 0
        self.connect_anim_timer.start()
        self._stop_idle_pulse()
        self.error_label.hide()
        self.toggle_anon.setEnabled(False)
        self._reset_transfer_metrics()
        self._show_toast("Connecting to Mirage...", level="info")

        tor = self.toggle_anon.isChecked()

        def do_connect():
            try:
                from wintun_client import WintunClient
                self.wintun_client = WintunClient(self.token, tor_mode=tor)
                self.wintun_client.connect()
                QMetaObject.invokeMethod(self, "_on_tun_connected", Qt.QueuedConnection)
            except Exception as e:
                # Clean up on failure
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

    def _disconnect(self):
        if hasattr(self, 'wintun_client') and self.wintun_client:
            client = self.wintun_client
            self.wintun_client = None
            threading.Thread(target=client.disconnect, daemon=True).start()
        self._apply_disconnected()
        if self.toggle_ks.isChecked():
            self._kill_switch_off()
        self._show_toast("VPN disconnected", level="info")
        QTimer.singleShot(3000, self._refresh_ip)

    @pyqtSlot()
    def _on_tun_connected(self):
        self.connected = True
        self.connect_anim_timer.stop()
        self.btn_connect.setObjectName("btnConnectActive")
        self.btn_connect.setText("DISCONNECT")
        self.btn_connect.setEnabled(True)
        self.btn_connect.style().unpolish(self.btn_connect)
        self.btn_connect.style().polish(self.btn_connect)
        self.status_label.setObjectName("labelStatusConnected")
        self.status_label.setText("CONNECTED")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        self.connect_time = time.time()
        self._last_bytes_time = self.connect_time
        self.timer.start()
        self.toggle_anon.setEnabled(False)
        self._show_toast("VPN connected — IP changing...", level="success")
        QTimer.singleShot(4000, self._refresh_ip)

    @pyqtSlot(str)
    def _on_tun_error(self, msg: str):
        self._apply_disconnected()
        self.error_label.setText(f"Error: {msg}")
        self.error_label.show()
        self._show_toast(msg, level="error")

    def _animate_connecting_label(self):
        dots = "." * ((self._connect_anim_step % 3) + 1)
        self.status_label.setText(f"CONNECTING{dots}")
        self._connect_anim_step += 1

    def _apply_disconnected(self):
        self.connected = False
        self.connect_anim_timer.stop()
        self.timer.stop()
        self.connect_time = None
        self.btn_connect.setObjectName("btnConnect")
        self.btn_connect.setText("CONNECT")
        self.btn_connect.setEnabled(True)
        self.btn_connect.style().unpolish(self.btn_connect)
        self.btn_connect.style().polish(self.btn_connect)
        self.status_label.setObjectName("labelStatus")
        self.status_label.setText("DISCONNECTED")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        self.lbl_duration.setText("Duration: 00:00")
        self.toggle_anon.setEnabled(True)
        self._reset_transfer_metrics()
        self._start_idle_pulse()

    def _reset_transfer_metrics(self):
        self._last_bytes_time = None
        self._last_sent = 0
        self._last_recv = 0
        self.lbl_up.setText("0 B")
        self.lbl_down.setText("0 B")
        self.rate_label.setText("UP 0 B/s | DOWN 0 B/s")

    def _start_idle_pulse(self):
        self.btn_connect_glow.setEnabled(True)
        self.btn_connect_glow.setColor(QColor(42, 90, 255, 90))
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

    def _update_timer(self):
        if self.connect_time:
            elapsed = int(time.time() - self.connect_time)
            m, s = divmod(elapsed, 60)
            h, m = divmod(m, 60)
            if h > 0:
                self.lbl_duration.setText(f"Duration: {h:02d}:{m:02d}:{s:02d}")
            else:
                self.lbl_duration.setText(f"Duration: {m:02d}:{s:02d}")

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


class DashboardWorker(QThread):
    data_ready = pyqtSignal(list, dict)

    def __init__(self):
        super().__init__()

    def run(self):
        try:
            SUPABASE_URL = "https://sjbymnijaogswmysubfu.supabase.co"
            SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNqYnltbmlqYW9nc3dteXN1YmZ1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3ODc1OTkyMSwiZXhwIjoyMDk0MzM1OTIxfQ.tkwFFX3l874OtpjyIY5V5go3rMZz6X-BqO_Nl0V73I8"

            # Fetch logs ordered by newest first
            req = urllib.request.Request(
                f"{SUPABASE_URL}/rest/v1/connection_logs?select=*&order=timestamp.desc&limit=100",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                }
            )
            with urllib.request.urlopen(req, timeout=10) as res:
                logs = json.loads(res.read())

            # Compute stats
            total_sent = sum(r.get("bytes_sent", 0) for r in logs)
            total_recv = sum(r.get("bytes_received", 0) for r in logs)
            connects   = sum(1 for r in logs if r.get("event") == "connect")
            stats = {
                "total_sent": total_sent,
                "total_recv": total_recv,
                "total_sessions": connects
            }
            self.data_ready.emit(logs, stats)
        except Exception as e:
            print(f"[-] Dashboard fetch error: {e}")
            self.data_ready.emit([], {})


class DashboardScreen(QWidget):
    def __init__(self, token: str):
        super().__init__()
        self.token = token
        self.setWindowTitle("Mirage — Dashboard")
        self.setMinimumSize(860, 580)
        self.setStyleSheet(STYLESHEET)
        self._build_ui()
        self._load_data()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#EDE9E3"))
        super().paintEvent(event)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        # Header
        header = QHBoxLayout()
        title = QLabel("DASHBOARD")
        title.setObjectName("labelTitle")
        title.setStyleSheet("font-size: 20px; letter-spacing: 5px;")
        header.addWidget(title)
        header.addStretch()

        btn_refresh = QPushButton("Refresh")
        btn_refresh.setObjectName("btnGhost")
        btn_refresh.setFixedHeight(34)
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.clicked.connect(self._load_data)
        header.addWidget(btn_refresh)

        btn_export = QPushButton("Export CSV")
        btn_export.setObjectName("btnGhost")
        btn_export.setFixedHeight(34)
        btn_export.setCursor(Qt.PointingHandCursor)
        btn_export.clicked.connect(self._export_csv)
        header.addWidget(btn_export)

        root.addLayout(header)

        # Stats row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        self.stat_sessions = self._stat_card("TOTAL SESSIONS", "—")
        self.stat_sent     = self._stat_card("DATA UPLOADED", "—")
        self.stat_recv     = self._stat_card("DATA DOWNLOADED", "—")
        stats_row.addWidget(self.stat_sessions[0])
        stats_row.addWidget(self.stat_sent[0])
        stats_row.addWidget(self.stat_recv[0])
        root.addLayout(stats_row)

        # Table
        table_label = QLabel("CONNECTION HISTORY")
        table_label.setObjectName("labelSection")
        root.addWidget(table_label)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Event", "IP Address", "Bytes Sent", "Bytes Received", "Timestamp", "User ID"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                background: rgba(255,255,255,0.45);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 16px;
                gridline-color: rgba(0,0,0,0.05);
            }
            QHeaderView::section {
                background: rgba(255,255,255,0.60);
                color: #9B968F;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 2px;
                padding: 8px;
                border: none;
            }
            QTableWidget::item {
                padding: 8px;
                color: #3D3A36;
                font-size: 12px;
            }
            QTableWidget::item:selected {
                background: rgba(42, 90, 255, 0.08);
            }
        """)
        root.addWidget(self.table)

        self.status_label = QLabel("Loading...")
        self.status_label.setObjectName("labelFieldName")
        self.status_label.setAlignment(Qt.AlignCenter)
        root.addWidget(self.status_label)

    def _stat_card(self, title, value):
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
        v.setStyleSheet("font-size: 20px; font-weight: 800; color: #2A5AFF;")
        layout.addWidget(t)
        layout.addWidget(v)
        return card, v

    def _load_data(self):
        self.status_label.setText("Loading...")
        self.worker = DashboardWorker()
        self.worker.data_ready.connect(self._on_data)
        self.worker.start()

    def _on_data(self, logs, stats):
        # Update stat cards
        self.stat_sessions[1].setText(str(stats.get("total_sessions", 0)))
        self.stat_sent[1].setText(format_bytes(stats.get("total_sent", 0)))
        self.stat_recv[1].setText(format_bytes(stats.get("total_recv", 0)))

        # Populate table
        self.table.setRowCount(len(logs))
        self._logs = logs
        for row, log in enumerate(logs):
            event = log.get("event", "")
            color = QColor(74, 158, 110) if event == "connect" else QColor(196, 86, 77)

            items = [
                event.upper(),
                log.get("ip_address", ""),
                format_bytes(log.get("bytes_sent", 0)),
                format_bytes(log.get("bytes_received", 0)),
                log.get("timestamp", "")[:19].replace("T", " "),
                str(log.get("user_id", ""))[:8] + "...",
            ]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                if col == 0:
                    item.setForeground(color)
                    item.setFont(QFont("", -1, QFont.Bold))
                self.table.setItem(row, col, item)

        self.status_label.setText(f"{len(logs)} records loaded")

    def _export_csv(self):
        if not hasattr(self, "_logs") or not self._logs:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "mirage_logs.csv", "CSV Files (*.csv)")
        if not path:
            return
        try:
            import csv
            with open(path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["event", "ip_address", "bytes_sent", "bytes_received", "timestamp", "user_id"])
                writer.writeheader()
                writer.writerows(self._logs)
        except Exception as e:
            print(f"[-] Export error: {e}")


class MirageApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mirage VPN")
        self.setMinimumSize(900, 620)
        self.setStyleSheet(STYLESHEET)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self._drag_pos = None

        # Restore firewall on any exit
        atexit.register(self._emergency_restore)

        # Handle CTRL+C and system signals
        signal.signal(signal.SIGTERM, self._signal_handler)
        if platform.system() != "Windows":
            signal.signal(signal.SIGHUP, self._signal_handler)

        # Ensure system-start safety net exists (best effort)
        self._ensure_startup_restore_task()

        self._show_login()

    def _build_title_bar(self):
        bar = QWidget()
        bar.setObjectName("titleBar")
        bar.setFixedHeight(38)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 6, 10, 4)
        layout.setSpacing(8)

        brand = QLabel("MIRAGE")
        brand.setStyleSheet("color: #8A857E; font-size: 11px; font-weight: 700; letter-spacing: 4px;")
        layout.addWidget(brand)
        layout.addStretch()

        btn_min = QToolButton()
        btn_min.setText("\u2013")
        btn_min.setFixedSize(24, 24)
        btn_min.setCursor(Qt.PointingHandCursor)
        btn_min.clicked.connect(self.showMinimized)
        layout.addWidget(btn_min)

        btn_close = QToolButton()
        btn_close.setText("\u2715")
        btn_close.setFixedSize(24, 24)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

        return bar

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.pos().y() < 42:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

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
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(0)
        wrapper_layout.addWidget(self._build_title_bar())

        screen = LoginScreen()
        screen.login_success.connect(self._on_login)
        wrapper_layout.addWidget(screen)

        self.setCentralWidget(wrapper)
        self.resize(980, 640)
        self._center()

    def _on_login(self, token: str, username: str):
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(0)
        wrapper_layout.addWidget(self._build_title_bar())

        screen = MainScreen(token, username)
        screen.logout_requested.connect(self._show_login)
        wrapper_layout.addWidget(screen)

        self.setCentralWidget(wrapper)
        self.resize(1060, 760)
        self._center()

    def _center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Mirage VPN")
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#EDE9E3"))
    palette.setColor(QPalette.WindowText, QColor("#3D3A36"))
    palette.setColor(QPalette.Base, QColor("#E8E4DE"))
    palette.setColor(QPalette.AlternateBase, QColor("#E3DFD9"))
    palette.setColor(QPalette.Text, QColor("#3D3A36"))
    palette.setColor(QPalette.Button, QColor("#E8E4DE"))
    palette.setColor(QPalette.ButtonText, QColor("#3D3A36"))
    palette.setColor(QPalette.Highlight, QColor("#2A5AFF"))
    palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(palette)

    window = MirageApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()