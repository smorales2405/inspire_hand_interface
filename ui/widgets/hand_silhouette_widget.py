from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont

FORCE_MAX_G = 1000


def _heatmap(grams: float, max_g: float = FORCE_MAX_G) -> QColor:
    """Blue (0 g) → green (mid) → red (max g)."""
    t = max(0.0, min(1.0, grams / max_g))
    return QColor.fromHsvF((1.0 - t) * 0.667, 0.80, 0.88)


class HandSilhouetteWidget(QWidget):
    """Right-hand palm-view schematic; each DOF region is colored by FORCE_ACT."""

    # Reference canvas: 260 × 300
    _W = 260.0
    _H = 300.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self._forces = [0.0] * 6
        self.setMinimumSize(230, 270)

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

        c  = [_heatmap(f) for f in self._forces]
        ol = QPen(QColor('#37474F'), 1.5)
        fnt_sm = QFont('Arial', max(6, int(7 * min(sx, sy))), QFont.Bold)
        fnt_xs = QFont('Arial', max(5, int(6 * min(sx, sy))), QFont.Bold)

        # ── 4 main fingers (left = índice, right = meñique) ─────────────
        for dof, x, yt, fw, fh, tag in (
            (3,  55, 20, 38, 122, "Índ."),
            (2,  96, 10, 38, 132, "Med."),
            (1, 137, 17, 38, 125, "Anu."),
            (0, 178, 35, 37, 107, "Men."),
        ):
            p.setBrush(QBrush(c[dof]))
            p.setPen(ol)
            p.drawRoundedRect(R(x, yt, fw, fh), 6 * sx, 6 * sy)
            p.setPen(QColor('white'))
            p.setFont(fnt_sm)
            p.drawText(R(x, yt + fh - 20, fw, 18), Qt.AlignCenter, tag)

        # ── Palm (neutral grey) ─────────────────────────────────────────
        p.setBrush(QBrush(QColor('#ECEFF1')))
        p.setPen(ol)
        p.drawRoundedRect(R(48, 135, 175, 100), 10 * sx, 10 * sy)

        # ── Thumb flex (DOF 4) — angled segment to the left of palm ─────
        # World centre (60, 162), rotated −42°; rect (−15, −62, 30, 65)
        p.save()
        p.translate(60 * sx, 162 * sy)
        p.rotate(-42)
        p.setBrush(QBrush(c[4]))
        p.setPen(ol)
        p.drawRoundedRect(QRectF(-15 * sx, -62 * sy, 30 * sx, 65 * sy), 6 * sx, 6 * sy)
        p.setPen(QColor('white'))
        p.setFont(fnt_sm)
        p.drawText(QRectF(-14 * sx, -18 * sy, 28 * sx, 16 * sy), Qt.AlignCenter, "P.fl.")
        p.restore()

        # ── Thumb rotation (DOF 5) ───────────────────────────────────────
        # World centre (56, 208), rotated −22°; rect (−13, −44, 27, 48)
        p.save()
        p.translate(56 * sx, 208 * sy)
        p.rotate(-22)
        p.setBrush(QBrush(c[5]))
        p.setPen(ol)
        p.drawRoundedRect(QRectF(-13 * sx, -44 * sy, 27 * sx, 48 * sy), 5 * sx, 5 * sy)
        p.setPen(QColor('white'))
        p.setFont(fnt_xs)
        p.drawText(QRectF(-13 * sx, -16 * sy, 27 * sx, 14 * sy), Qt.AlignCenter, "P.rot")
        p.restore()

        # ── Colour scale bar (right margin) ──────────────────────────────
        bx, by, bw, bh = 228, 68, 11, 160
        for i in range(bh):
            clr = _heatmap((bh - 1 - i) / (bh - 1) * FORCE_MAX_G)
            p.setPen(QPen(clr, 1))
            p.drawLine(int(bx * sx), int((by + i) * sy),
                       int((bx + bw) * sx), int((by + i) * sy))
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
        p.drawText(R(48, 252, 175, 14), Qt.AlignCenter,
                   "Vista palmar — Mano Derecha")
