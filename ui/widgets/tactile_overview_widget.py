from PyQt5.QtWidgets import QWidget, QToolTip
from PyQt5.QtCore import Qt, QRectF, pyqtSignal, QPointF
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont

from core.tactile_zones import ZONES, N_ZONES

TAXEL_MAX = 4000   # raw ADC ceiling for colour mapping


def _heatmap(val: float, max_v: float = TAXEL_MAX) -> QColor:
    """Blue (0) → green (mid) → red (max)."""
    t = max(0.0, min(1.0, val / max_v))
    return QColor.fromHsvF((1.0 - t) * 0.667, 0.85, 0.90)


def _zone_mean(data):
    if not data:
        return 0.0
    return sum(max(0, v) for v in data) / len(data)


# ── Anatomical geometry on reference canvas 200 × 320 ──────────────────────
# Each zone: (zone_index, x, y, w, h)  — all in reference coords
#   Fingers: Meñique(0), Anular(1), Medio(2), Índice(3) — left to right on palm view
#   Each finger column: Punta (top), Distal, Palmar  — top to bottom
#   Thumb: to the left side (rotated column)
#   Palm: full-width band at bottom

_CW = 200.0   # canvas width
_CH = 320.0   # canvas height

# finger columns (dedo): x_start, width per column
_FCOLS = [
    (  9, 28),   # Meñique  (z0-z2)
    ( 42, 28),   # Anular   (z3-z5)
    ( 75, 28),   # Medio    (z6-z8)
    (108, 28),   # Índice   (z9-z11)
]
# Finger zone heights: Punta, Distal, Palmar
_FH = [18, 60, 48]
# Finger y-offsets (top of column from canvas top) — Meñique shorter
_FTOP = [30, 20, 10, 20]   # Meñique, Anular, Medio, Índice

# Build finger zones
_FINGER_ZONES = []
for col, (zbase, (cx, cw)) in enumerate(zip([0, 3, 6, 9], _FCOLS)):
    ytop = _FTOP[col]
    for row, zh in enumerate(_FH):
        _FINGER_ZONES.append((zbase + row, cx, ytop, cw, zh))
        ytop += zh + 2   # 2-px gap between zones

# Thumb column: vertical on the right side of canvas
# Zones: Punta(12), Distal(13), Medio(14), Palmar(15)
_TH = [18, 60, 18, 60]
_THUMB_ZONES = []
_tx, _tw = 144, 28
_ty = 30
for zi, th in zip([12, 13, 14, 15], _TH):
    _THUMB_ZONES.append((zi, _tx, _ty, _tw, th))
    _ty += th + 2

# Palm zone (z16)
_PALM_Y = 140
_PALM_H = 80
_PALM_ZONES = [(16, 5, _PALM_Y, 172, _PALM_H)]

_ALL_ZONES_GEOM = _FINGER_ZONES + _THUMB_ZONES + _PALM_ZONES


class TactileOverviewWidget(QWidget):
    """Anatomical hand overview: 17 tactile zones coloured by mean taxel value.

    Emits zone_clicked(index) when a zone is clicked.
    Reference canvas: 200 × 320. Scale to widget size at paint time.
    """

    zone_clicked = pyqtSignal(int)

    _W = _CW
    _H = _CH

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data  = [None] * N_ZONES   # list[int] per zone
        self._selected = -1
        self._hovered  = -1
        self.setMinimumSize(200, 320)
        self.setMouseTracking(True)

    def update_data(self, zone_data_list):
        """Receive all-zones data (list of list[int])."""
        self._data = zone_data_list
        self.update()

    def set_selected(self, idx: int):
        self._selected = idx
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        self._draw(p)
        p.end()

    def _sx(self):
        return self.width()  / self._W

    def _sy(self):
        return self.height() / self._H

    def _R(self, x, y, w, h) -> QRectF:
        sx, sy = self._sx(), self._sy()
        return QRectF(x * sx, y * sy, w * sx, h * sy)

    def _draw(self, p: QPainter):
        sx, sy = self._sx(), self._sy()
        W, H = self.width(), self.height()

        p.fillRect(0, 0, W, H, QColor('#F5F5F5'))

        ol     = QPen(QColor('#37474F'), 1.2)
        ol_sel = QPen(QColor('#FF6F00'), 2.5)
        ol_hov = QPen(QColor('#1565C0'), 1.8)

        fnt = QFont('Arial', max(5, int(6 * min(sx, sy))), QFont.Bold)
        p.setFont(fnt)

        for zi, x, y, w, h in _ALL_ZONES_GEOM:
            rect = self._R(x, y, w, h)
            data = self._data[zi]
            mean = _zone_mean(data) if data else 0.0
            fill = _heatmap(mean)

            if zi == self._selected:
                pen = ol_sel
            elif zi == self._hovered:
                pen = ol_hov
            else:
                pen = ol

            p.setBrush(QBrush(fill))
            p.setPen(pen)
            p.drawRoundedRect(rect, 3 * sx, 3 * sy)

            # Short label inside zone
            name = ZONES[zi][0]
            short = name.split('—')[-1].strip()[:6]
            p.setPen(QColor('white') if mean > TAXEL_MAX * 0.3 else QColor('#37474F'))
            p.drawText(rect, Qt.AlignCenter, short)

        # ── Colour scale bar ──────────────────────────────────────────────
        bx, by, bw, bh = 178, 10, 10, 200
        for i in range(bh):
            clr = _heatmap((bh - 1 - i) / (bh - 1) * TAXEL_MAX)
            p.setPen(QPen(clr, 1))
            p.drawLine(int(bx * sx), int((by + i) * sy),
                       int((bx + bw) * sx), int((by + i) * sy))
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor('#37474F'), 1))
        p.drawRect(self._R(bx, by, bw, bh))

        p.setPen(QColor('#37474F'))
        p.setFont(QFont('Arial', max(5, int(6 * min(sx, sy)))))
        p.drawText(self._R(bx - 14, by - 12, bw + 28, 11), Qt.AlignCenter,
                   f"{TAXEL_MAX}")
        p.drawText(self._R(bx - 8, by + bh + 2, bw + 16, 11), Qt.AlignCenter, "0")

        # ── Finger labels at top ──────────────────────────────────────────
        labels = ["Men.", "Anu.", "Med.", "Índ.", "Pulg."]
        for col, (cx, cw) in enumerate(_FCOLS):
            p.setPen(QColor('#546E7A'))
            p.setFont(QFont('Arial', max(5, int(5 * min(sx, sy)))))
            p.drawText(self._R(cx, 0, cw, 10), Qt.AlignCenter, labels[col])
        p.drawText(self._R(_tx, 0, _tw, 10), Qt.AlignCenter, labels[4])

        # ── Palm label ────────────────────────────────────────────────────
        p.setPen(QColor('#546E7A'))
        p.setFont(QFont('Arial', max(5, int(6 * min(sx, sy)))))
        p.drawText(self._R(5, _PALM_Y + _PALM_H + 2, 172, 12),
                   Qt.AlignCenter, "Palma")

    def _zone_at(self, px: float, py: float) -> int:
        sx, sy = self._sx(), self._sy()
        for zi, x, y, w, h in _ALL_ZONES_GEOM:
            if x * sx <= px <= (x + w) * sx and y * sy <= py <= (y + h) * sy:
                return zi
        return -1

    def mouseMoveEvent(self, event):
        zi = self._zone_at(event.x(), event.y())
        if zi != self._hovered:
            self._hovered = zi
            self.update()
        if zi >= 0:
            name = ZONES[zi][0]
            data = self._data[zi]
            mean = _zone_mean(data) if data else 0.0
            QToolTip.showText(event.globalPos(),
                              f"{name}\nMedia: {mean:.0f}  Max: {max(data) if data else 0}")
        else:
            QToolTip.hideText()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            zi = self._zone_at(event.x(), event.y())
            if zi >= 0:
                self._selected = zi
                self.update()
                self.zone_clicked.emit(zi)

    def leaveEvent(self, event):
        self._hovered = -1
        self.update()
