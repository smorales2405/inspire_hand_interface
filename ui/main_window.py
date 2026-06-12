from PyQt5.QtWidgets import QMainWindow, QTabWidget
from PyQt5.QtGui import QFont

from core.hand_connection import HandConnection
from ui.tabs.control_tab import ControlTab
from ui.tabs.force_tab import ForceTab
from ui.tabs.tactile_tab import TactileTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.hand = HandConnection()
        self._build_ui()

    def _build_ui(self):
        self.setWindowTitle("Inspire Hand RH56DFTP — Interface de Control")
        self.setMinimumSize(1100, 660)

        self._tabs = QTabWidget()
        self._tabs.setFont(QFont('Arial', 10))

        # Phase 1: control + angle reading
        self._control_tab = ControlTab(self.hand)
        self._tabs.addTab(self._control_tab, "Control y Angulos")

        # Phase 2: force heatmap + bars + temporal curves
        self._force_tab = ForceTab(self.hand)
        self._tabs.addTab(self._force_tab, "Lectura Fuerzas")

        # Phase 3: tactile sensor anatomical layout + detail view
        self._tactile_tab = TactileTab(self.hand)
        self._tabs.addTab(self._tactile_tab, "Sensores Tactiles")

        self.setCentralWidget(self._tabs)
        self.statusBar().showMessage(
            "Inspire Hand RH56DFTP Interface  |  Desconectado"
        )

    def closeEvent(self, event):
        self.hand.disconnect()
        event.accept()
