import sys
import os

# Make the parent workspace importable (inspire_sdkpy, unitree_sdk2_python, etc.)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont
from ui.main_window import MainWindow

_STYLE = """
QMainWindow, QWidget {
    background-color: #ECEFF1;
}
QGroupBox {
    font-weight: bold;
    border: 1px solid #BDBDBD;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 6px;
    background-color: #FFFFFF;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: #37474F;
}
QLabel {
    background-color: transparent;
}
QTabWidget::pane {
    border: 1px solid #BDBDBD;
    border-radius: 4px;
}
QTabBar::tab {
    background: #CFD8DC;
    border: 1px solid #B0BEC5;
    padding: 6px 18px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected {
    background: #FFFFFF;
    border-bottom-color: #FFFFFF;
    font-weight: bold;
}
QTabBar::tab:hover:!selected {
    background: #B0BEC5;
}
QSlider::groove:horizontal {
    height: 6px;
    background: #CFD8DC;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    width: 16px;
    height: 16px;
    margin: -5px 0;
    background: #1565C0;
    border-radius: 8px;
}
QSlider::sub-page:horizontal {
    background: #90CAF9;
    border-radius: 3px;
}
QDoubleSpinBox, QSpinBox, QLineEdit, QComboBox {
    border: 1px solid #BDBDBD;
    border-radius: 4px;
    padding: 2px 4px;
    background: #FFFFFF;
}
QDoubleSpinBox:focus, QSpinBox:focus, QLineEdit:focus {
    border-color: #1565C0;
}
"""


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setFont(QFont('Arial', 10))
    app.setStyleSheet(_STYLE)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
