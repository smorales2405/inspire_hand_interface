import time
from collections import deque

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QColor, QPen, QFont

DOF_COLORS  = ['#E91E63', '#9C27B0', '#2196F3', '#009688', '#FF5722', '#795548']
FORCE_MAX_G = 1000
WINDOW_S    = 20.0   # seconds of history shown
MAX_SAMPLES = 500

_ML, _MR, _MT, _MB = 52, 98, 14, 34   # plot margins (px)

_LEGEND_SHORT = ["Men.", "Anu.", "Med.", "Índ.", "P.fl.", "P.rot"]


class ForcePlotWidget(QWidget):
    """Scrolling time-series of FORCE_ACT for all 6 DOFs (QPainter-based)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._buf = deque(maxlen=MAX_SAMPLES)   # (monotonic_t, [6 floats])
        self.setMinimumHeight(145)
        self.setMinimumWidth(360)

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
        p.setFont(QFont('Consolas', 8))
        for i in range(5):
            gy = _MT + int(i * ph / 4)
            p.setPen(QPen(QColor('#EEEEEE'), 1))
            p.drawLine(_ML, gy, _ML + pw, gy)
            g_val = int(FORCE_MAX_G * (1 - i / 4))
            p.setPen(QColor('#546E7A'))
            p.drawText(0, gy - 8, _ML - 4, 16,
                       Qt.AlignRight | Qt.AlignVCenter, str(g_val))

        # ── Y-axis label ─────────────────────────────────────────────────
        p.save()
        p.setPen(QColor('#546E7A'))
        p.setFont(QFont('Arial', 8))
        p.translate(9, _MT + ph // 2)
        p.rotate(-90)
        p.drawText(-24, -6, 48, 13, Qt.AlignCenter, "fuerza (g)")
        p.restore()

        # ── Plot border ──────────────────────────────────────────────────
        p.setPen(QPen(QColor('#BDBDBD'), 1))
        p.drawRect(_ML, _MT, pw, ph)

        # ── No-data placeholder ──────────────────────────────────────────
        if len(self._buf) < 2:
            p.setPen(QColor('#9E9E9E'))
            p.setFont(QFont('Arial', 9))
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

        # ── X-axis labels ────────────────────────────────────────────────
        p.setFont(QFont('Consolas', 8))
        p.setPen(QColor('#546E7A'))
        for i in range(5):
            tx  = _ML + int(i / 4 * pw)
            rel = int(-WINDOW_S * (1 - i / 4))
            lbl = f"{rel}s" if rel != 0 else "0s"
            p.drawText(tx - 18, _MT + ph + 4, 36, _MB - 6,
                       Qt.AlignCenter, lbl)

        self._draw_legend(p, W)

    def _draw_legend(self, p: QPainter, W: int):
        lx = W - _MR + 6
        p.setFont(QFont('Arial', 8))
        for dof in range(6):
            ly = _MT + dof * 20
            p.setPen(QPen(QColor(DOF_COLORS[dof]), 2))
            p.drawLine(lx, ly + 8, lx + 14, ly + 8)
            p.setPen(QColor('#37474F'))
            p.drawText(lx + 17, ly, _MR - 24, 16,
                       Qt.AlignLeft | Qt.AlignVCenter, _LEGEND_SHORT[dof])
