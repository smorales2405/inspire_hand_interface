from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont

FORCE_MAX_G = 3000


def _heatmap(grams: float, max_g: float = FORCE_MAX_G) -> QColor:
    """Blue (0 g) → green (mid) → red (max g)."""
    t = max(0.0, min(1.0, grams / max_g))
    return QColor.fromHsvF((1.0 - t) * 0.667, 0.80, 0.88)


class HandSilhouetteWidget(QWidget):
    """Right-hand palm-view schematic; each DOF region is colored by FORCE_ACT.

    Geometry reference canvas: 260 × 300.
    Proportions are scaled to the actual widget size at paint time.
    """

    _W = 260.0
    _H = 300.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self._forces = [0.0] * 6
        self.setMinimumSize(220, 270)

    def update_forces(self, forces):
        self._forces = (list(forces) + [0.0] * 6)[:6]
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        self._draw(p)
        p.end()

    def _draw(self, p: QPainter):
        sx = self.width()  / self._W
        sy = self.height() / self._H

        def R(x, y, w, h) -> QRectF:
            return QRectF(x * sx, y * sy, w * sx, h * sy)

        c   = [_heatmap(f) for f in self._forces]
        ol  = QPen(QColor('#37474F'), 1.5)
        fsm = QFont('Arial', max(6, int(7 * min(sx, sy))), QFont.Bold)
        fxs = QFont('Arial', max(5, int(6 * min(sx, sy))), QFont.Bold)

        # ── 4 main fingers: thinner and longer (left=índice, right=meñique) ─
        #   (dof, x_left, y_top, width, height, tag)
        for dof, x, yt, fw, fh, tag in (
            (3,  80, 15, 20, 135, "Índ."),   # index
            (2, 103,  5, 20, 145, "Med."),   # middle — tallest
            (1, 126, 12, 20, 138, "Anu."),   # ring
            (0, 149, 40, 19, 110, "Men."),   # pinky — shortest
        ):
            p.setBrush(QBrush(c[dof]))
            p.setPen(ol)
            p.drawRoundedRect(R(x, yt, fw, fh), 5 * sx, 5 * sy)
            p.setPen(QColor('white'))
            p.setFont(fsm)
            p.drawText(R(x, yt + fh - 20, fw, 18), Qt.AlignCenter, tag)

        # ── Palm: narrower and taller ────────────────────────────────────
        p.setBrush(QBrush(QColor('#ECEFF1')))
        p.setPen(ol)
        p.drawRoundedRect(R(76, 145, 97, 120), 9 * sx, 9 * sy)

        # ── Thumb flex (DOF 4) ────────────────────────────────────────────
        # centre (65, 172), rotate −40°, rect (−12, −56, 24, 60)
        p.save()
        p.translate(65 * sx, 172 * sy)
        p.rotate(-40)
        p.setBrush(QBrush(c[4]))
        p.setPen(ol)
        p.drawRoundedRect(QRectF(-12 * sx, -56 * sy, 24 * sx, 60 * sy), 5 * sx, 5 * sy)
        p.setPen(QColor('white'))
        p.setFont(fsm)
        p.drawText(QRectF(-11 * sx, -18 * sy, 22 * sx, 16 * sy), Qt.AlignCenter, "P.fl.")
        p.restore()

        # ── Thumb rotation (DOF 5) ────────────────────────────────────────
        # centre (60, 218), rotate −22°, rect (−11, −40, 22, 44)
        p.save()
        p.translate(60 * sx, 218 * sy)
        p.rotate(-22)
        p.setBrush(QBrush(c[5]))
        p.setPen(ol)
        p.drawRoundedRect(QRectF(-11 * sx, -40 * sy, 22 * sx, 44 * sy), 5 * sx, 5 * sy)
        p.setPen(QColor('white'))
        p.setFont(fxs)
        p.drawText(QRectF(-11 * sx, -14 * sy, 22 * sx, 13 * sy), Qt.AlignCenter, "P.rot")
        p.restore()

        # ── Colour-scale bar (right margin) ──────────────────────────────
        bx, by, bw, bh = 190, 55, 12, 170
        for i in range(bh):
            clr = _heatmap((bh - 1 - i) / (bh - 1) * FORCE_MAX_G)
            p.setPen(QPen(clr, 1))
            p.drawLine(int(bx * sx), int((by + i) * sy),
                       int((bx + bw) * sx), int((by + i) * sy))
        # border only — no fill (brush cleared to avoid covering the gradient)
        p.setBrush(Qt.NoBrush)
        p.setPen(ol)
        p.drawRect(R(bx, by, bw, bh))
        p.setPen(QColor('#37474F'))
        p.setFont(QFont('Arial', max(6, int(7 * min(sx, sy)))))
        p.drawText(R(bx - 8, by - 14, bw + 16, 12), Qt.AlignCenter,
                   f"{FORCE_MAX_G} g")
        p.drawText(R(bx - 4, by + bh + 2, bw + 8, 12), Qt.AlignCenter, "0 g")

        # ── Caption ──────────────────────────────────────────────────────
        p.setPen(QColor('#546E7A'))
        p.setFont(QFont('Arial', max(7, int(8 * min(sx, sy)))))
        p.drawText(R(76, 278, 97, 14), Qt.AlignCenter,
                   "Vista palmar — Mano Derecha")
