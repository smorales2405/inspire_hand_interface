from PyQt5.QtWidgets import (
    QFrame, QGridLayout, QLabel, QSlider, QDoubleSpinBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from core.angle_converter import DOF_ANGLE_RANGES, register_to_degrees, degrees_to_register

# Status code → (hex color, display text)
_STATUS = {
    0: ('#2196F3', 'Abriendo'),
    1: ('#FF9800', 'Cerrando'),
    2: ('#4CAF50', 'En posición'),
    3: ('#FF9800', 'Límite de fuerza'),
    5: ('#F44336', 'Prot. corriente'),
    6: ('#F44336', 'Motor bloqueado'),
    7: ('#F44336', 'Fallo actuador'),
}

# One accent color per DOF for the left border
_DOF_COLORS = ['#E91E63', '#9C27B0', '#2196F3', '#009688', '#FF5722', '#795548']


class FingerWidget(QFrame):
    """Single-DOF control: slider + spinbox for target angle, label for actual angle."""

    angle_changed = pyqtSignal(int, int)   # (dof_index, register_value)

    def __init__(self, dof_index: int, name: str, parent=None):
        super().__init__(parent)
        self.dof_index = dof_index
        self.name = name
        self.min_deg, self.max_deg = DOF_ANGLE_RANGES[dof_index]
        self._color = _DOF_COLORS[dof_index]
        self._build_ui()

    # ── UI ───────────────────────────────────────────────────────────

    def _build_ui(self):
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setStyleSheet(
            f"FingerWidget {{"
            f"  border-left: 5px solid {self._color};"
            f"  border-radius: 4px;"
            f"  background-color: #FAFAFA;"
            f"}}"
        )

        g = QGridLayout(self)
        g.setContentsMargins(10, 6, 12, 6)
        g.setHorizontalSpacing(8)
        g.setVerticalSpacing(3)

        # Col 0: DOF name (spans both rows)
        name_lbl = QLabel(self.name)
        name_lbl.setFixedWidth(110)
        name_lbl.setFont(QFont('Arial', 10, QFont.Bold))
        name_lbl.setStyleSheet(f"color: {self._color}; background: transparent;")
        g.addWidget(name_lbl, 0, 0, 2, 1, Qt.AlignVCenter)

        # ── Row 0: target (set) ──────────────────────────────────────
        g.addWidget(self._lbl("Objetivo:"), 0, 1)

        min_lbl = self._lbl(f"{self.min_deg:.1f}°")
        min_lbl.setFixedWidth(42)
        min_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        min_lbl.setStyleSheet("color: #9E9E9E; background: transparent;")
        g.addWidget(min_lbl, 0, 2)

        self.slider = QSlider(Qt.Horizontal)
        # Use tenths-of-degree as integer units for sub-degree precision
        self.slider.setRange(int(self.min_deg * 10), int(self.max_deg * 10))
        self.slider.setValue(int(self.max_deg * 10))   # default: fully open
        self.slider.setMinimumWidth(190)
        g.addWidget(self.slider, 0, 3)

        max_lbl = self._lbl(f"{self.max_deg:.1f}°")
        max_lbl.setFixedWidth(42)
        max_lbl.setStyleSheet("color: #9E9E9E; background: transparent;")
        g.addWidget(max_lbl, 0, 4)

        self.spinbox = QDoubleSpinBox()
        self.spinbox.setRange(self.min_deg, self.max_deg)
        self.spinbox.setDecimals(1)
        self.spinbox.setSuffix(" °")
        self.spinbox.setValue(self.max_deg)
        self.spinbox.setFixedWidth(90)
        self.spinbox.setAlignment(Qt.AlignRight)
        g.addWidget(self.spinbox, 0, 5)

        # ── Row 1: actual (read) ─────────────────────────────────────
        g.addWidget(self._lbl("Real:"), 1, 1)

        self.actual_lbl = QLabel("— °")
        self.actual_lbl.setFont(QFont('Arial', 13, QFont.Bold))
        self.actual_lbl.setStyleSheet("color: #1565C0; background: transparent;")
        self.actual_lbl.setMinimumWidth(100)
        g.addWidget(self.actual_lbl, 1, 2, 1, 2)   # span 2 cols

        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet(
            "color: #BDBDBD; font-size: 12px; background: transparent;"
        )
        self.status_dot.setFixedWidth(16)
        g.addWidget(self.status_dot, 1, 4)

        self.status_lbl = QLabel("Sin conexión")
        self.status_lbl.setStyleSheet("color: #757575; background: transparent;")
        self.status_lbl.setFixedWidth(140)
        g.addWidget(self.status_lbl, 1, 5)

        # Signals
        self.slider.valueChanged.connect(self._on_slider)
        self.spinbox.valueChanged.connect(self._on_spinbox)

    @staticmethod
    def _lbl(text):
        l = QLabel(text)
        l.setStyleSheet("background: transparent;")
        return l

    # ── Slots ────────────────────────────────────────────────────────

    def _on_slider(self, tenths):
        self.spinbox.blockSignals(True)
        self.spinbox.setValue(tenths / 10.0)
        self.spinbox.blockSignals(False)
        self.angle_changed.emit(
            self.dof_index,
            degrees_to_register(tenths / 10.0, self.dof_index)
        )

    def _on_spinbox(self, deg):
        self.slider.blockSignals(True)
        self.slider.setValue(int(deg * 10))
        self.slider.blockSignals(False)
        self.angle_changed.emit(
            self.dof_index,
            degrees_to_register(deg, self.dof_index)
        )

    # ── Public API ───────────────────────────────────────────────────

    def set_actual_angle(self, register_val: int, status: int = None):
        """Update the 'Real' readout and status indicator."""
        deg = register_to_degrees(register_val, self.dof_index)
        self.actual_lbl.setText(f"{deg:.1f} °")
        if status is not None:
            color, text = _STATUS.get(status, ('#BDBDBD', f'Estado {status}'))
            self.status_dot.setStyleSheet(
                f"color: {color}; font-size: 12px; background: transparent;"
            )
            self.status_lbl.setText(text)

    def set_register_value(self, reg_val: int):
        """Sync slider and spinbox to a register value without emitting angle_changed."""
        deg = register_to_degrees(reg_val, self.dof_index)
        self.slider.blockSignals(True)
        self.spinbox.blockSignals(True)
        self.slider.setValue(int(deg * 10))
        self.spinbox.setValue(deg)
        self.slider.blockSignals(False)
        self.spinbox.blockSignals(False)
