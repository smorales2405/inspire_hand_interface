import time
from collections import deque

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QColor, QPen, QFont

DOF_COLORS  = ['#E91E63', '#9C27B0', '#2196F3', '#009688', '#FF5722', '#795548']
FORCE_MAX_G = 3000
WINDOW_S    = 20.0   # seconds of history shown
MAX_SAMPLES = 500

_ML, _MR, _MT, _MB = 62, 148, 16, 44   # plot margins (px)

_LEGEND_NAMES = ["Meñique", "Anular", "Medio", "Índice",
                 "Pulgar (flex.)", "Pulgar (rot.)"]


class ForcePlotWidget(QWidget):
    """Scrolling time-series of FORCE_ACT for all 6 DOFs (QPainter-based).

    X axis: 0 s (oldest sample in window) → 20 s (current sample).
    Y axis: 0 g → FORCE_MAX_G.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._buf = deque(maxlen=MAX_SAMPLES)   # (monotonic_t, [6 floats])
        self.setMinimumHeight(150)
        self.setMinimumWidth(380)

    def push_sample(self, forces):
        self._buf.append((time.monotonic(), list(forces)))
        self.update()

    def clear(self):
        self._buf.clear()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        self._draw(p)
        p.end()

    def _draw(self, p: QPainter):
        W, H = self.width(), self.height()
        pw = W - _ML - _MR
        ph = H - _MT - _MB
        if pw < 30 or ph < 20:
            return

        # ── Background ───────────────────────────────────────────────────
        p.fillRect(0, 0, W, H, QColor('#FAFAFA'))
        p.fillRect(_ML, _MT, pw, ph, QColor('#FFFFFF'))

        # ── Horizontal grid + Y labels ───────────────────────────────────
        p.setFont(QFont('Consolas', 10))
        for i in range(5):
            gy = _MT + int(i * ph / 4)
            p.setPen(QPen(QColor('#EEEEEE'), 1))
            p.drawLine(_ML, gy, _ML + pw, gy)
            g_val = int(FORCE_MAX_G * (1 - i / 4))
            p.setPen(QColor('#37474F'))
            p.drawText(0, gy - 10, _ML - 5, 20,
                       Qt.AlignRight | Qt.AlignVCenter, str(g_val))

        # ── Y-axis label ─────────────────────────────────────────────────
        p.save()
        p.setPen(QColor('#37474F'))
        p.setFont(QFont('Arial', 10, QFont.Bold))
        p.translate(11, _MT + ph // 2)
        p.rotate(-90)
        p.drawText(-32, -7, 64, 14, Qt.AlignCenter, "fuerza (g)")
        p.restore()

        # ── Plot border ──────────────────────────────────────────────────
        p.setPen(QPen(QColor('#BDBDBD'), 1))
        p.drawRect(_ML, _MT, pw, ph)

        # ── No-data placeholder ──────────────────────────────────────────
        if len(self._buf) < 2:
            p.setPen(QColor('#9E9E9E'))
            p.setFont(QFont('Arial', 11))
            p.drawText(_ML, _MT, pw, ph, Qt.AlignCenter,
                       "Sin datos — conecte la mano")
            self._draw_legend(p, W)
            return

        t_now = self._buf[-1][0]
        t0    = t_now - WINDOW_S

        def px(t: float) -> int:
            return _ML + int((t - t0) / WINDOW_S * pw)

        def py(g: float) -> int:
            return _MT + ph - int(max(0.0, min(1.0, g / FORCE_MAX_G)) * ph)

        # ── Draw one line per DOF ────────────────────────────────────────
        for dof in range(6):
            pts = [(px(t), py(v[dof])) for t, v in self._buf if t >= t0]
            if len(pts) < 2:
                continue
            p.setPen(QPen(QColor(DOF_COLORS[dof]), 2,
                          Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            for i in range(1, len(pts)):
                x0, y0 = pts[i - 1]
                x1, y1 = pts[i]
                if _ML <= x1 <= _ML + pw:
                    p.drawLine(x0, y0, x1, y1)

        # ── X-axis labels: 0 s (oldest) → 20 s (current) ────────────────
        p.setFont(QFont('Consolas', 10))
        p.setPen(QColor('#37474F'))
        for i in range(5):
            tx  = _ML + int(i / 4 * pw)
            lbl = f"{int(WINDOW_S * i / 4)}s"
            p.drawText(tx - 20, _MT + ph + 5, 40, _MB - 8,
                       Qt.AlignCenter, lbl)

        # ── X-axis label ─────────────────────────────────────────────────
        p.setFont(QFont('Arial', 10, QFont.Bold))
        p.drawText(_ML, _MT + ph + 5, pw, _MB - 8, Qt.AlignCenter,
                   "tiempo (s)")

        self._draw_legend(p, W)

    def _draw_legend(self, p: QPainter, W: int):
        lx = W - _MR + 8
        p.setFont(QFont('Arial', 10))
        for dof in range(6):
            ly = _MT + dof * 22
            p.setPen(QPen(QColor(DOF_COLORS[dof]), 2))
            p.drawLine(lx, ly + 9, lx + 16, ly + 9)
            p.setPen(QColor('#37474F'))
            p.drawText(lx + 20, ly, _MR - 30, 18,
                       Qt.AlignLeft | Qt.AlignVCenter, _LEGEND_NAMES[dof])
