from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

DOF_COLORS  = ['#E91E63', '#9C27B0', '#2196F3', '#009688', '#FF5722', '#795548']
_SHORT_NAMES = ["Men.", "Anu.", "Med.", "Índ.", "P.fl.", "P.rot"]
FORCE_MAX_G = 3000


class ForceBarWidget(QWidget):
    """Vertical single-DOF force display: value on top, bar in middle, name at bottom."""

    def __init__(self, dof_index: int, name: str, parent=None):
        super().__init__(parent)
        self._color = DOF_COLORS[dof_index]
        self._short = _SHORT_NAMES[dof_index]
        self.setMinimumWidth(48)
        self.setToolTip(name)
        self._build_ui()

    def _build_ui(self):
        col = QVBoxLayout(self)
        col.setContentsMargins(3, 4, 3, 4)
        col.setSpacing(4)

        self._num = QLabel("0 g")
        self._num.setAlignment(Qt.AlignCenter)
        self._num.setFont(QFont('Consolas', 9))
        self._num.setStyleSheet(
            f"color: {self._color}; font-weight: bold; background: transparent;"
        )
        col.addWidget(self._num)

        self._bar = QProgressBar()
        self._bar.setOrientation(Qt.Vertical)
        self._bar.setRange(0, FORCE_MAX_G)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setMinimumHeight(80)
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
        col.addWidget(self._bar, stretch=1)

        lbl = QLabel(self._short)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFont(QFont('Arial', 9, QFont.Bold))
        lbl.setStyleSheet(f"color: {self._color}; background: transparent;")
        col.addWidget(lbl)

    def set_force(self, grams: float):
        self._bar.setValue(int(max(0, min(FORCE_MAX_G, grams))))
        self._num.setText(f"{int(grams)} g")
