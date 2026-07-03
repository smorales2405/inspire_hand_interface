from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox
)
from PyQt5.QtCore import QTimer

from core.angle_converter import DOF_NAMES
from ui.widgets.hand_silhouette_widget import HandSilhouetteWidget
from ui.widgets.force_bar_widget import ForceBarWidget
from ui.widgets.force_plot_widget import ForcePlotWidget


class ForceTab(QWidget):
    """Phase-2 tab: hand-silhouette heatmap + FORCE_ACT bars + temporal curves."""

    def __init__(self, hand_connection, parent=None):
        super().__init__(parent)
        self.hand = hand_connection
        self._build_ui()
        self._timer = QTimer(self)
        self._timer.setInterval(100)   # 10 Hz
        self._timer.timeout.connect(self._refresh)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # ── Top row: silhouette (left) + bars (right) ───────────────────
        top = QHBoxLayout()
        top.setSpacing(10)

        sil_grp = QGroupBox("Silueta — Distribución de Fuerza")
        sil_lay = QVBoxLayout(sil_grp)
        sil_lay.setContentsMargins(6, 6, 6, 6)
        self._sil = HandSilhouetteWidget()
        sil_lay.addWidget(self._sil)
        top.addWidget(sil_grp, stretch=3)

        bars_grp = QGroupBox("FORCE_ACT por DOF")
        bars_lay = QHBoxLayout(bars_grp)
        bars_lay.setContentsMargins(8, 10, 8, 8)
        bars_lay.setSpacing(6)
        self._bars: list[ForceBarWidget] = []
        for i, name in enumerate(DOF_NAMES):
            fb = ForceBarWidget(i, name)
            bars_lay.addWidget(fb, stretch=1)
            self._bars.append(fb)
        top.addWidget(bars_grp, stretch=2)

        root.addLayout(top, stretch=3)

        # ── Bottom row: temporal curves ─────────────────────────────────
        plot_grp = QGroupBox("Evolución Temporal de Fuerzas")
        plot_lay = QVBoxLayout(plot_grp)
        plot_lay.setContentsMargins(6, 6, 6, 6)
        self._plot = ForcePlotWidget()
        plot_lay.addWidget(self._plot)
        root.addWidget(plot_grp, stretch=2)

    # ── Visibility hooks — only poll Modbus when this tab is active ──────

    def showEvent(self, event):
        self._timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self._timer.stop()
        super().hideEvent(event)

    # ── 10 Hz refresh ────────────────────────────────────────────────────

    def _refresh(self):
        if not self.hand.connected:
            return
        forces = self.hand.read_forces()
        if forces is None:
            return
        for i, fb in enumerate(self._bars):
            fb.set_force(forces[i] if i < len(forces) else 0)
        self._sil.update_forces(forces)
        self._plot.push_sample(forces)
