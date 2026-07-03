from PyQt5.QtWidgets import QWidget, QToolTip, QSizePolicy
from PyQt5.QtCore import Qt, QRectF, pyqtSignal
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


# ── Anatomical geometry — reference canvas 210 × 270 ───────────────────────
#
# Right-hand palm view (thumb on left, pinky on right).
# Heights proportional to taxel row counts; joint gaps separate phalanges.
#
#  Heights (px):
#    Punta  (3 rows)  = 14
#    Distal (12 rows) = 56
#    Palmar (10 rows) = 46
#    Palm   (14 rows) = 65
#    Thumb Medio (3 rows) = 14 (unique mid-joint sensor)
#
#  Gaps (px):
#    inter-phalangeal joint = 10
#    metacarpal gap (phalange → palm) = 18

_CW = 210.0
_CH = 270.0

_PH  = 14   # Punta height
_DH  = 56   # Distal height
_LH  = 46   # Palmar height (10 rows)
_PaH = 65   # Palm height (14 rows)
_JG  = 10   # joint gap
_MG  = 18   # metacarpal gap (last phalanx → palm)

_FW  = 26   # finger zone width (8 taxel columns)

# x-origin of each column
_TX = 5    # Thumb (Pulgar)
_IX = 46   # Índice   (+ 15 px anatomical thumb–index gap)
_MX = 77   # Medio    (+ 5 px gap)
_AX = 108  # Anular
_NX = 139  # Meñique

# Finger column y-tops (stagger reflects natural finger length differences)
_IT = 26   # Índice
_MT = 14   # Medio    ← tallest
_AT = 26   # Anular
_NT = 52   # Meñique  ← shortest

# Palm top = Medio_top + Punta + gap + Distal + gap + Palmar + metacarpal_gap
_PALM_Y = _MT + _PH + _JG + _DH + _JG + _LH + _MG   # = 14+14+10+56+10+46+18 = 168
_PALM_X = _IX   # starts under Índice
_PALM_W = _NX + _FW - _IX  # spans all 4 main fingers  = 119

# Thumb y-start: at roughly the mid-finger level (anatomically the thumb is
# shorter and more lateral; its base is near the middle phalanx of the index)
_TY = 68

def _col_zones(zbase, x, ytop):
    """3 zones (Punta, Distal, Palmar) for a main finger column."""
    return [
        (zbase,     x, ytop,                          _FW, _PH),
        (zbase + 1, x, ytop + _PH + _JG,              _FW, _DH),
        (zbase + 2, x, ytop + _PH + _JG + _DH + _JG, _FW, _LH),
    ]

_FINGER_ZONES = (
    _col_zones(9,  _IX, _IT) +   # Índice  (z9-z11)
    _col_zones(6,  _MX, _MT) +   # Medio   (z6-z8)
    _col_zones(3,  _AX, _AT) +   # Anular  (z3-z5)
    _col_zones(0,  _NX, _NT)     # Meñique (z0-z2)
)

# Thumb: 4 zones, Punta → Distal → Medio (small) → Palmar
_ty0 = _TY
_ty1 = _ty0 + _PH  + _JG           # Distal start
_ty2 = _ty1 + _DH  + _JG           # Medio start
_ty3 = _ty2 + _PH  + _JG           # Palmar start   (Thumb Medio = Punta height)
_THUMB_ZONES = [
    (12, _TX, _ty0, _FW, _PH),    # Punta
    (13, _TX, _ty1, _FW, _DH),    # Distal
    (14, _TX, _ty2, _FW, _PH),    # Medio (3×3)
    (15, _TX, _ty3, _FW, _DH),    # Palmar (12×8)
]

_PALM_ZONES = [(16, _PALM_X, _PALM_Y, _PALM_W, _PaH)]

_ALL_ZONES_GEOM = _FINGER_ZONES + _THUMB_ZONES + _PALM_ZONES

# Column header labels
_COL_LABELS = [
    (_TX, "Pulg."),
    (_IX, "Índ."),
    (_MX, "Med."),
    (_AX, "Anu."),
    (_NX, "Men."),
]

# Colour-scale bar (right of hand)
_BAR_X, _BAR_Y, _BAR_W, _BAR_H = 177, 12, 18, 230


class TactileOverviewWidget(QWidget):
    """Anatomical right-hand palm view: 17 tactile zones coloured by mean taxel value.

    Emits zone_clicked(index) on left-click. Scales to widget size at paint time.
    Reference canvas: 210 × 270.
    """

    zone_clicked = pyqtSignal(int)

    _W = _CW
    _H = _CH

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data     = [None] * N_ZONES
        self._selected = -1
        self._hovered  = -1
        self.setMinimumSize(210, 270)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)

    def update_data(self, zone_data_list):
        self._data = zone_data_list
        self.update()

    def set_selected(self, idx: int):
        self._selected = idx
        self.update()

    # ── Paint ────────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        self._draw(p)
        p.end()

    def _sx(self): return self.width()  / self._W
    def _sy(self): return self.height() / self._H

    def _R(self, x, y, w, h) -> QRectF:
        sx, sy = self._sx(), self._sy()
        return QRectF(x * sx, y * sy, w * sx, h * sy)

    def _draw(self, p: QPainter):
        sx, sy = self._sx(), self._sy()
        W, H   = self.width(), self.height()

        p.fillRect(0, 0, W, H, QColor('#F0F4F8'))

        ol     = QPen(QColor('#37474F'), 1.2)
        ol_sel = QPen(QColor('#FF6F00'), 2.5)
        ol_hov = QPen(QColor('#1565C0'), 2.0)

        fnt_zone = QFont('Arial', max(5, int(6 * min(sx, sy))), QFont.Bold)
        p.setFont(fnt_zone)

        for zi, x, y, w, h in _ALL_ZONES_GEOM:
            rect = self._R(x, y, w, h)
            data = self._data[zi]
            mean = _zone_mean(data) if data else 0.0
            fill = _heatmap(mean)

            pen = ol_sel if zi == self._selected else (ol_hov if zi == self._hovered else ol)
            p.setBrush(QBrush(fill))
            p.setPen(pen)
            p.drawRoundedRect(rect, 3 * sx, 3 * sy)

            # label only for zones tall enough to read text
            if h * sy >= 18:
                short = ZONES[zi][0].split('—')[-1].strip()[:5]
                p.setPen(QColor('white') if mean > TAXEL_MAX * 0.25 else QColor('#263238'))
                p.drawText(rect, Qt.AlignCenter, short)

        # ── Column headers ────────────────────────────────────────────────
        hdr_fnt = QFont('Arial', max(5, int(5.5 * min(sx, sy))), QFont.Bold)
        p.setFont(hdr_fnt)
        p.setPen(QColor('#546E7A'))
        for cx, lbl in _COL_LABELS:
            p.drawText(self._R(cx, 0, _FW, 13), Qt.AlignCenter, lbl)

        # ── Colour-scale bar ─────────────────────────────────────────────
        bx, by, bw, bh = _BAR_X, _BAR_Y, _BAR_W, _BAR_H
        for i in range(bh):
            clr = _heatmap((bh - 1 - i) / (bh - 1) * TAXEL_MAX)
            p.setPen(QPen(clr, 1))
            p.drawLine(int(bx * sx), int((by + i) * sy),
                       int((bx + bw) * sx), int((by + i) * sy))
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor('#37474F'), 1))
        p.drawRect(self._R(bx, by, bw, bh))

        bar_fnt = QFont('Arial', max(5, int(6 * min(sx, sy))))
        p.setFont(bar_fnt)
        p.setPen(QColor('#37474F'))
        p.drawText(self._R(bx - 10, by - 14, bw + 20, 13), Qt.AlignCenter,
                   f"{TAXEL_MAX}")
        p.drawText(self._R(bx - 6, by + bh + 2, bw + 12, 13), Qt.AlignCenter, "0")

    # ── Hit testing ──────────────────────────────────────────────────────────

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
            data = self._data[zi]
            mean = _zone_mean(data) if data else 0.0
            mx   = max(data) if data else 0
            QToolTip.showText(event.globalPos(),
                              f"{ZONES[zi][0]}\nMedia: {mean:.0f}   Máx: {mx}")
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
