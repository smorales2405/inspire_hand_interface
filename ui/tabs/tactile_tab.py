from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGroupBox, QLabel
)
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

from core.tactile_zones import N_ZONES
from ui.widgets.tactile_overview_widget import TactileOverviewWidget
from ui.widgets.tactile_detail_widget import TactileDetailWidget


class _TactileReaderThread(QThread):
    """Background thread: reads all 17 zones at ~5 Hz and emits data_ready."""

    data_ready = pyqtSignal(object)   # list[list[int]]

    def __init__(self, hand_connection):
        super().__init__()
        self._hand    = hand_connection
        self._running = False

    def run(self):
        self._running = True
        while self._running:
            if self._hand.connected:
                data = self._hand.read_all_tactile_zones()
                if data is not None:
                    self.data_ready.emit(data)
            self.msleep(200)   # ~5 Hz

    def stop(self):
        self._running = False
        self.wait(1000)


class TactileTab(QWidget):
    """Phase-3 tab: anatomical tactile overview (left) + zone detail (right).

    Background QThread performs all Modbus reads so the UI never blocks.
    """

    def __init__(self, hand_connection, parent=None):
        super().__init__(parent)
        self.hand = hand_connection
        self._thread = _TactileReaderThread(hand_connection)
        self._build_ui()
        self._thread.data_ready.connect(self._on_data)

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(10)

        # ── Left: anatomical overview ────────────────────────────────────
        ov_grp = QGroupBox("Vista Anatómica — Zonas Táctiles")
        ov_grp.setFont(QFont('Arial', 10, QFont.Bold))
        ov_lay = QVBoxLayout(ov_grp)
        ov_lay.setContentsMargins(6, 8, 6, 6)

        self._overview = TactileOverviewWidget()
        self._overview.zone_clicked.connect(self._on_zone_clicked)
        ov_lay.addWidget(self._overview)

        hint = QLabel("Haga clic en una zona para ver detalle")
        hint.setAlignment(__import__('PyQt5.QtCore', fromlist=['Qt']).Qt.AlignCenter)
        hint.setFont(QFont('Arial', 9))
        hint.setStyleSheet("color: #9E9E9E;")
        ov_lay.addWidget(hint)

        root.addWidget(ov_grp, stretch=2)

        # ── Right: zone detail ───────────────────────────────────────────
        det_grp = QGroupBox("Detalle de Zona")
        det_grp.setFont(QFont('Arial', 10, QFont.Bold))
        det_lay = QVBoxLayout(det_grp)
        det_lay.setContentsMargins(6, 8, 6, 6)

        self._detail = TactileDetailWidget()
        det_lay.addWidget(self._detail)

        root.addWidget(det_grp, stretch=3)

        # ── Status label ─────────────────────────────────────────────────
        self._last_data = None
        self._selected_zone = -1

    # ── Visibility hooks ─────────────────────────────────────────────────

    def showEvent(self, event):
        if not self._thread.isRunning():
            self._thread.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self._thread.stop()
        super().hideEvent(event)

    def closeEvent(self, event):
        self._thread.stop()
        super().closeEvent(event)

    # ── Slots ─────────────────────────────────────────────────────────────

    def _on_data(self, data):
        self._last_data = data
        self._overview.update_data(data)
        if self._selected_zone >= 0:
            self._detail.show_zone(self._selected_zone,
                                   data[self._selected_zone])

    def _on_zone_clicked(self, zone_idx: int):
        self._selected_zone = zone_idx
        self._overview.set_selected(zone_idx)
        data = self._last_data[zone_idx] if self._last_data else None
        self._detail.show_zone(zone_idx, data)
