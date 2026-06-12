from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont

from core.tactile_zones import ZONES
from ui.widgets.tactile_overview_widget import TAXEL_MAX, _heatmap


class _TaxelGridWidget(QWidget):
    """Draws a heatmap grid for a single tactile zone."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data   = []
        self._shape  = (1, 1)
        self.setMinimumSize(160, 160)

    def set_zone(self, data, shape):
        self._data  = data or []
        self._shape = shape
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        self._draw(p)
        p.end()

    def _draw(self, p: QPainter):
        W, H = self.width(), self.height()
        rows, cols = self._shape

        cell_w = W / cols
        cell_h = H / rows

        if not self._data:
            p.fillRect(0, 0, W, H, QColor('#EEEEEE'))
            p.setPen(QColor('#9E9E9E'))
            p.setFont(QFont('Arial', 10))
            p.drawText(0, 0, W, H, Qt.AlignCenter, "Sin datos")
            return

        for idx, val in enumerate(self._data[: rows * cols]):
            r   = idx // cols
            c   = idx  % cols
            clr = _heatmap(max(0, val))
            rect = QRectF(c * cell_w, r * cell_h, cell_w, cell_h)
            p.fillRect(rect, clr)

        # light grid lines
        p.setPen(QPen(QColor(0, 0, 0, 30), 0.5))
        for r in range(rows + 1):
            y = r * cell_h
            p.drawLine(QRectF(0, y, W, 0).topLeft(),
                       QRectF(W, y, 0, 0).topLeft())
        for c in range(cols + 1):
            x = c * cell_w
            p.drawLine(QRectF(x, 0, 0, H).topLeft(),
                       QRectF(x, H, 0, 0).topLeft())


class TactileDetailWidget(QWidget):
    """Shows detailed taxel grid + stats for a selected zone."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._zone_idx = -1

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(6)

        self._title = QLabel("— Seleccione una zona —")
        self._title.setAlignment(Qt.AlignCenter)
        self._title.setFont(QFont('Arial', 11, QFont.Bold))
        self._title.setStyleSheet("color: #37474F;")
        lay.addWidget(self._title)

        self._grid = _TaxelGridWidget()
        lay.addWidget(self._grid, stretch=1)

        self._stats = QLabel("")
        self._stats.setAlignment(Qt.AlignCenter)
        self._stats.setFont(QFont('Consolas', 9))
        self._stats.setStyleSheet("color: #546E7A;")
        lay.addWidget(self._stats)

    def show_zone(self, zone_idx: int, data):
        self._zone_idx = zone_idx
        name, _, n_regs, shape = ZONES[zone_idx]
        self._title.setText(name)
        self._grid.set_zone(data, shape)

        if data:
            active = sum(1 for v in data if v > 0)
            mx     = max(data)
            mean   = sum(max(0, v) for v in data) / len(data)
            self._stats.setText(
                f"Taxeles: {n_regs}   Activos: {active}   "
                f"Máx: {mx}   Media: {mean:.1f}"
            )
        else:
            self._stats.setText("Sin datos")

    def clear(self):
        self._title.setText("— Seleccione una zona —")
        self._grid.set_zone([], (1, 1))
        self._stats.setText("")
