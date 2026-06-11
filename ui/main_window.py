from PyQt5.QtWidgets import QMainWindow, QTabWidget, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from core.hand_connection import HandConnection
from ui.tabs.control_tab import ControlTab


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

        # Placeholder tabs for phases 2 and 3
        for title in ("Fuerzas y Silueta", "Sensores Tactiles"):
            lbl = QLabel(f"  {title}  —  proxima fase")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #9E9E9E; font-size: 14pt;")
            self._tabs.addTab(lbl, title)

        self.setCentralWidget(self._tabs)
        self.statusBar().showMessage(
            "Inspire Hand RH56DFTP Interface  |  Desconectado"
        )

    def closeEvent(self, event):
        self.hand.disconnect()
        event.accept()
