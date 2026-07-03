from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont

# Each entry: (name, [step1, step2, ...])
# step = [little, ring, middle, index, thumb_flex, thumb_rot]
# register 0  → max angle → fully closed (max flexion)
# register 1000 → min angle → fully open (extended)
#
# Pinza DOF values derived from target degrees:
#   index  100° → reg 486   range [19, 176.7]
#   t.flex  15° → reg 580   range [-13, 53.6]
#   t.rot  155° → reg 133   range [90, 165]
GESTURES = [
    ("Abrir",         [[1000, 1000, 1000, 1000, 1000, 1000]]),
    ("Cerrar",        [[   0,    0,    0,    0, 1000, 1000],   # 4 fingers close first
                       [   0,    0,    0,    0,    0, 1000]]), # then thumb flex closes
    ("Señalar",       [[   0,    0,    0, 1000,    0,  500]]),
    ("Pinza",         [[1000, 1000, 1000,  486,  580,  133]]),

    ("Pulgar arriba", [[   0,    0,    0,    0, 1000, 1000]]),
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

_STEP_DELAY_MS = 800  # ms between sequential gesture steps


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

        for name, steps in GESTURES:
            btn = QPushButton(name)
            btn.setMinimumHeight(34)
            btn.setFont(QFont('Arial', 10))
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(_BTN_STYLE)
            btn.clicked.connect(
                lambda _checked, s=steps: self._emit_steps(s)
            )
            layout.addWidget(btn)

        layout.addStretch()
        layout.addWidget(self._build_speed_section())

    def _emit_steps(self, steps):
        """Emit step 0 immediately; schedule subsequent steps with a fixed delay."""
        self.gesture_selected.emit(list(steps[0]))
        for i, step in enumerate(steps[1:], start=1):
            QTimer.singleShot(
                i * _STEP_DELAY_MS,
                lambda s=step: self.gesture_selected.emit(list(s))
            )

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
