from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

# Register values per gesture: [little, ring, middle, index, thumb_bend, thumb_rot]
#   0 = fully open / extended
#   1000 = fully closed / bent
GESTURES = [
    ("Abierta",        [   0,    0,    0,    0,    0,  500]),
    ("Puno",           [1000, 1000, 1000, 1000, 1000,  500]),
    ("Senyalar",       [1000, 1000, 1000,    0, 1000,  500]),
    ("Tijeras",        [1000, 1000,    0,    0, 1000,  500]),
    ("Tres dedos",     [1000,    0,    0,    0, 1000,  500]),
    ("Pinza",          [1000, 1000, 1000,  500,  600,  300]),
    ("OK",             [   0,    0,    0,  700,  600,  300]),
    ("Pulgar arriba",  [1000, 1000, 1000, 1000,    0,  500]),
]

_BTN_STYLE = (
    "QPushButton {"
    "  background-color: #E3F2FD;"
    "  border: 1px solid #90CAF9;"
    "  border-radius: 4px;"
    "  padding: 4px 6px;"
    "  text-align: left;"
    "}"
    "QPushButton:hover  { background-color: #BBDEFB; }"
    "QPushButton:pressed{ background-color: #64B5F6; }"
)


class GesturePanel(QFrame):
    gesture_selected = pyqtSignal(list)   # list[int] of 6 register values
    speed_changed    = pyqtSignal(int)    # 0-1000

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        title = QLabel("Gestos Predefinidos")
        title.setFont(QFont('Arial', 11, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("background: transparent;")
        layout.addWidget(title)

        for name, values in GESTURES:
            btn = QPushButton(name)
            btn.setMinimumHeight(34)
            btn.setFont(QFont('Arial', 10))
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(_BTN_STYLE)
            btn.clicked.connect(
                lambda _checked, v=values: self.gesture_selected.emit(list(v))
            )
            layout.addWidget(btn)

        layout.addStretch()
        layout.addWidget(self._build_speed_section())

    def _build_speed_section(self):
        frame = QFrame()
        frame.setStyleSheet("background: transparent;")
        v = QVBoxLayout(frame)
        v.setContentsMargins(0, 6, 0, 0)
        v.setSpacing(3)

        lbl = QLabel("Velocidad de movimiento")
        lbl.setFont(QFont('Arial', 9, QFont.Bold))
        lbl.setStyleSheet("background: transparent;")
        v.addWidget(lbl)

        row = QHBoxLayout()
        row.addWidget(QLabel("Lento"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(100, 1000)
        self.speed_slider.setValue(500)
        row.addWidget(self.speed_slider)
        row.addWidget(QLabel("Rapido"))
        v.addLayout(row)

        self._speed_val_lbl = QLabel("500")
        self._speed_val_lbl.setAlignment(Qt.AlignCenter)
        self._speed_val_lbl.setStyleSheet("color: #555; font-size: 9pt; background: transparent;")
        v.addWidget(self._speed_val_lbl)

        self.speed_slider.valueChanged.connect(self._on_speed)
        return frame

    def _on_speed(self, val):
        self._speed_val_lbl.setText(str(val))
        self.speed_changed.emit(val)
