from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QProgressBar
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

DOF_COLORS  = ['#E91E63', '#9C27B0', '#2196F3', '#009688', '#FF5722', '#795548']
FORCE_MAX_G = 1000


class ForceBarWidget(QWidget):
    """Single-DOF force display: colored bar + numeric value in grams."""

    def __init__(self, dof_index: int, name: str, parent=None):
        super().__init__(parent)
        self._color = DOF_COLORS[dof_index]
        self._build_ui(name)

    def _build_ui(self, name: str):
        row = QHBoxLayout(self)
        row.setContentsMargins(2, 1, 2, 1)
        row.setSpacing(6)

        dot = QLabel("●")
        dot.setStyleSheet(f"color: {self._color}; background: transparent;")
        dot.setFixedWidth(14)
        row.addWidget(dot)

        lbl = QLabel(name)
        lbl.setFixedWidth(104)
        lbl.setFont(QFont('Arial', 9))
        row.addWidget(lbl)

        self._bar = QProgressBar()
        self._bar.setRange(0, FORCE_MAX_G)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(16)
        self._bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #BDBDBD;
                border-radius: 3px;
                background: #F5F5F5;
            }}
            QProgressBar::chunk {{
                background-color: {self._color};
                border-radius: 2px;
            }}
        """)
        row.addWidget(self._bar, stretch=1)

        self._num = QLabel("    0 g")
        self._num.setFixedWidth(58)
        self._num.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._num.setFont(QFont('Consolas', 9))
        row.addWidget(self._num)

    def set_force(self, grams: float):
        self._bar.setValue(int(max(0, min(FORCE_MAX_G, grams))))
        self._num.setText(f"{int(grams):5d} g")
