from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QSpinBox, QGroupBox, QComboBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from core.angle_converter import DOF_NAMES
from ui.widgets.finger_widget import FingerWidget
from ui.widgets.gesture_panel import GesturePanel


class ControlTab(QWidget):
    def __init__(self, hand_connection, parent=None):
        super().__init__(parent)
        self.hand = hand_connection
        self.current_angles = [0] * 6   # register values, default: all open
        self._build_ui()
        self._setup_timer()

    # ── UI construction ──────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        root.addWidget(self._build_conn_panel())

        body = QHBoxLayout()
        body.setSpacing(10)
        body.addWidget(self._build_fingers_group(), stretch=4)
        body.addWidget(self._build_gesture_panel(), stretch=0)
        root.addLayout(body)

    # Connection panel ─────────────────────────────────────────────

    def _build_conn_panel(self):
        grp = QGroupBox("Conexion")
        row = QHBoxLayout(grp)
        row.setContentsMargins(8, 4, 8, 4)

        row.addWidget(QLabel("Modo:"))
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["TCP/IP", "RS-485 Serial"])
        self._mode_combo.setFixedWidth(130)
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        row.addWidget(self._mode_combo)

        row.addSpacing(10)

        # TCP fields
        self._tcp_w = QWidget()
        tcp = QHBoxLayout(self._tcp_w)
        tcp.setContentsMargins(0, 0, 0, 0)
        tcp.addWidget(QLabel("IP:"))
        self._ip = QLineEdit("192.168.11.210")
        self._ip.setFixedWidth(145)
        tcp.addWidget(self._ip)
        tcp.addWidget(QLabel("Puerto:"))
        self._port = QSpinBox()
        self._port.setRange(1, 65535)
        self._port.setValue(6000)
        self._port.setFixedWidth(70)
        tcp.addWidget(self._port)
        row.addWidget(self._tcp_w)

        # Serial fields
        self._serial_w = QWidget()
        ser = QHBoxLayout(self._serial_w)
        ser.setContentsMargins(0, 0, 0, 0)
        ser.addWidget(QLabel("Puerto serial:"))
        self._serial_port = QLineEdit("/dev/ttyUSB0")
        self._serial_port.setFixedWidth(130)
        ser.addWidget(self._serial_port)
        row.addWidget(self._serial_w)
        self._serial_w.hide()

        row.addSpacing(10)
        row.addWidget(QLabel("ID:"))
        self._dev_id = QSpinBox()
        self._dev_id.setRange(1, 254)
        self._dev_id.setValue(1)
        self._dev_id.setFixedWidth(55)
        row.addWidget(self._dev_id)

        row.addSpacing(10)
        row.addWidget(QLabel("Mano:"))
        self._lr_combo = QComboBox()
        self._lr_combo.addItems(["Derecha (R)", "Izquierda (L)"])
        self._lr_combo.setFixedWidth(130)
        row.addWidget(self._lr_combo)

        row.addStretch()

        self._conn_btn = QPushButton("Conectar")
        self._conn_btn.setFixedWidth(115)
        self._conn_btn.setFont(QFont('Arial', 10, QFont.Bold))
        self._conn_btn.setStyleSheet(
            "background-color:#4CAF50; color:white; border-radius:4px; padding:4px;"
        )
        self._conn_btn.setCursor(Qt.PointingHandCursor)
        self._conn_btn.clicked.connect(self._toggle_connection)
        row.addWidget(self._conn_btn)

        self._conn_status = QLabel("  Desconectado")
        self._conn_status.setStyleSheet("color:#F44336; font-weight:bold;")
        self._conn_status.setFixedWidth(155)
        row.addWidget(self._conn_status)

        grp.setMaximumHeight(72)
        return grp

    # Finger controls ──────────────────────────────────────────────

    def _build_fingers_group(self):
        grp = QGroupBox("Control y Lectura de Angulos")
        v = QVBoxLayout(grp)
        v.setSpacing(5)
        v.setContentsMargins(8, 10, 8, 8)

        self._finger_widgets: list[FingerWidget] = []
        for i, name in enumerate(DOF_NAMES):
            fw = FingerWidget(i, name)
            fw.angle_changed.connect(self._on_angle_changed)
            v.addWidget(fw)
            self._finger_widgets.append(fw)

        return grp

    # Gesture panel ────────────────────────────────────────────────

    def _build_gesture_panel(self):
        self._gp = GesturePanel()
        self._gp.gesture_selected.connect(self._apply_gesture)
        self._gp.speed_changed.connect(self._on_speed_changed)
        self._gp.setFixedWidth(215)
        return self._gp

    # ── Timer ────────────────────────────────────────────────────────

    def _setup_timer(self):
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_state)

    # ── Slots ────────────────────────────────────────────────────────

    def _on_mode_changed(self, index):
        self._tcp_w.setVisible(index == 0)
        self._serial_w.setVisible(index == 1)

    def _toggle_connection(self):
        if self.hand.connected:
            self._timer.stop()
            self.hand.disconnect()
            self._conn_btn.setText("Conectar")
            self._conn_btn.setStyleSheet(
                "background-color:#4CAF50; color:white; border-radius:4px; padding:4px;"
            )
            self._conn_status.setText("  Desconectado")
            self._conn_status.setStyleSheet("color:#F44336; font-weight:bold;")
        else:
            dev_id = self._dev_id.value()
            if self._mode_combo.currentIndex() == 0:
                ok, msg = self.hand.connect_tcp(
                    ip=self._ip.text(),
                    port=self._port.value(),
                    device_id=dev_id,
                )
            else:
                ok, msg = self.hand.connect_serial(
                    port=self._serial_port.text(),
                    device_id=dev_id,
                )

            if ok:
                self._conn_btn.setText("Desconectar")
                self._conn_btn.setStyleSheet(
                    "background-color:#F44336; color:white; border-radius:4px; padding:4px;"
                )
                self._conn_status.setText("  Conectado")
                self._conn_status.setStyleSheet("color:#4CAF50; font-weight:bold;")
                self._sync_sliders_to_hand()
                self._timer.start(100)   # 10 Hz read cycle
            else:
                self._conn_status.setText(f"  Error: {msg[:28]}")
                self._conn_status.setStyleSheet("color:#F44336;")

    def _sync_sliders_to_hand(self):
        """After connecting, read current angles and update sliders to avoid jumps."""
        state = self.hand.read_state()
        if not state:
            return
        for i, fw in enumerate(self._finger_widgets):
            val = state['angle_act'][i]
            if val is not None and 0 <= val <= 1000:
                self.current_angles[i] = val
                fw.set_register_value(val)

    def _refresh_state(self):
        state = self.hand.read_state()
        if state is None:
            return
        angles   = state.get('angle_act', [0] * 6)
        statuses = state.get('status',    [0] * 6)
        for i, fw in enumerate(self._finger_widgets):
            fw.set_actual_angle(
                angles[i]   if i < len(angles)   else 0,
                statuses[i] if i < len(statuses) else None,
            )

    def _on_angle_changed(self, dof_index: int, reg_val: int):
        self.current_angles[dof_index] = reg_val
        if self.hand.connected:
            self.hand.set_angles(self.current_angles)

    def _apply_gesture(self, register_values: list):
        self.current_angles = list(register_values)
        for i, fw in enumerate(self._finger_widgets):
            fw.set_register_value(register_values[i])
        if self.hand.connected:
            self.hand.set_angles(self.current_angles)

    def _on_speed_changed(self, speed_val: int):
        if self.hand.connected:
            self.hand.set_speed(speed_val)
