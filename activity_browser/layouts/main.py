# -*- coding: utf-8 -*-
import importlib.util
import traceback
import sys
import shutil

from PySide2 import QtCore, QtGui, QtWidgets

from ..ui.icons import qicons
from ..ui.menu_bar import MenuBar
from ..ui.statusbar import Statusbar
from ..ui.style import header
from ..ui.utils import StdRedirector
from .panels import LeftPanel, RightPanel, BottomPanel, Database_Manager_Panel 
from .tabs.project_manager import ProjectsWidget
from .tabs import MethodsTab
from ..signals import signals


class MainWindow(QtWidgets.QMainWindow):
    DEFAULT_NO_METHOD = 'No method selected yet'

    def __init__(self, parent):
        super(MainWindow, self).__init__(None)

        self.setLocale(QtCore.QLocale(QtCore.QLocale.English, QtCore.QLocale.UnitedStates))
        self.parent = parent

        # Window title
        self.setWindowTitle("Activity Browser")

        # Small icon in main window titlebar
        self.icon = qicons.ab
        self.setWindowIcon(self.icon)

        # setting-up dockwidgets
        self.projects=QtWidgets.QDockWidget('Projects')
        self.projects.setWidget(ProjectsWidget())
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.projects)

        self.projects=QtWidgets.QDockWidget('Databases')
        self.projects.setWidget(Database_Manager_Panel(self))
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.projects)

        self.impacts=QtWidgets.QDockWidget('Impact Categories')
        self.impacts.setWidget(MethodsTab(self.impacts))
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.impacts)

        self.setTabPosition(QtCore.Qt.AllDockWidgetAreas, QtWidgets.QTabWidget.North)
        self.setDockOptions(self.GroupedDragging | self.AllowTabbedDocks )


        # Debug/... window stack
        self.debug = QtWidgets.QWidget()
        self.debug.icon = qicons.debug
        self.debug.name = "&Debug Window"

        self.stacked = QtWidgets.QStackedWidget()
        self.stacked.addWidget(self.debug)
        # End of Debug/... window stack

        self.setCentralWidget(RightPanel(self))

        # Layout: extra items outside main layout
        self.menu_bar = MenuBar(self)
        self.setMenuBar(self.menu_bar)
        self.status_bar = Statusbar(self)
        self.setStatusBar(self.status_bar)

        self.connect_signals()
        self.debug_window = False

    def closeEvent(self,event):
        self.parent.close()

    def connect_signals(self):
        # Keyboard shortcuts
        self.shortcut_debug = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+D"), self)
        self.shortcut_debug.activated.connect(self.toggle_debug_window)
        signals.restore_cursor.connect(self.restore_user_control)

    def toggle_debug_window(self):
        """Toggle the bottom debug window"""
        self.debug_window = not self.debug_window
        self.bottom_panel.setVisible(self.debug_window)

    def add_tab_to_panel(self, obj, label, side):
        panel = self.left_panel if side == 'left' else self.right_panel
        panel.add_tab(obj, label)

    def select_tab(self, obj, side):
        panel = self.left_panel if side == 'left' else self.right_panel
        panel.setCurrentIndex(panel.indexOf(obj))

    def dialog(self, title, label):
        value, ok = QtWidgets.QInputDialog.getText(self, title, label)
        if ok:
            return value

    def info(self, label):
        QtWidgets.QMessageBox.information(
            self,
            "Information",
            label,
            QtWidgets.QMessageBox.Ok,
        )

    def warning(self, title, text):
        QtWidgets.QMessageBox.warning(self, title, text)

    def confirm(self, label):
        response = QtWidgets.QMessageBox.question(
            self,
            "Confirm Action",
            label,
            QtWidgets.QMessageBox.Yes,
            QtWidgets.QMessageBox.No
        )
        return response == QtWidgets.QMessageBox.Yes

    def restore_user_control(self):
        QtWidgets.QApplication.restoreOverrideCursor()