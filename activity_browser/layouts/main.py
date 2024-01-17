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
                
        self.setTabPosition(QtCore.Qt.AllDockWidgetAreas, QtWidgets.QTabWidget.West)
        self.setDockOptions(self.AllowNestedDocks | self.AllowTabbedDocks )

        databases_widget_bar = WidgetBar("Reference Flows", self)
        self.databases=QtWidgets.QDockWidget('Databases')
        self.databases.setWidget(Database_Manager_Panel(self))
        databases_widget_bar.addDockWidget(self.databases)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, databases_widget_bar)

        ic_widget_bar = WidgetBar("Impact Categories", self)
        self.ic=QtWidgets.QDockWidget('Impact Categories')
        self.ic.setWidget(MethodsTab(self.ic))
        ic_widget_bar.addDockWidget(self.ic)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, ic_widget_bar)
        self.tabifyDockWidget(databases_widget_bar, ic_widget_bar)

        parameters_widget_bar = WidgetBar("Parameters", self)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, parameters_widget_bar)
        self.tabifyDockWidget(databases_widget_bar, parameters_widget_bar)

        scenarios_widget_bar = WidgetBar("Scenarios", self)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, scenarios_widget_bar)
        self.tabifyDockWidget(databases_widget_bar, scenarios_widget_bar)

        """
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, projects_widget_bar)

        self.projects=QtWidgets.QDockWidget('Projects')
        self.projects.setWidget(ProjectsWidget())
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.projects)
        widget_bar.addDockWidget(self.projects)

        self.databases=QtWidgets.QDockWidget('Databases')
        self.databases.setWidget(Database_Manager_Panel(self))
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.databases)
        widget_bar.addDockWidget(self.databases)

        self.impacts=QtWidgets.QDockWidget('Impact Categories')
        self.impacts.setWidget(MethodsTab(self.impacts))
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.impacts)
        """



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

        self.menu_bar.view_menu.addSeparator()
        #self.menu_bar.view_menu.addAction(self.projects.toggleViewAction())
        #self.menu_bar.view_menu.addAction(self.databases.toggleViewAction())
        #self.menu_bar.view_menu.addAction(self.impacts.toggleViewAction())

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
        menubars = self.findChildren(WidgetBar)
        for bar in menubars:
            bar.collapse()

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

class WidgetBar(QtWidgets.QDockWidget):
    def __init__(self, title: str , parent):
        super().__init__(title, parent)
        self.setFeatures(self.NoDockWidgetFeatures)

        # initialize docker
        self.docker = QtWidgets.QMainWindow()
        self.docker.setDockOptions(self.docker.AnimatedDocks)

        self.title_bar = QtWidgets.QWidget(self)
        self.title_bar.setFixedHeight(1)
        self.title_bar.setMinimumHeight(1)

        self.setWidget(self.docker)
        self.setTitleBarWidget(self.title_bar)       

        # initialize spacer for in the docker
        self.spacer = QtWidgets.QWidget(self)
        self.spacer.setFixedHeight(1)

        self.spacer_title = QtWidgets.QWidget(self)
        self.spacer_title.setFixedHeight(1)

        spacer_dock = QtWidgets.QDockWidget(self)
        spacer_dock.setWidget(self.spacer)
        spacer_dock.setTitleBarWidget(self.spacer_title)
        self.addDockWidget(spacer_dock)
      
    def addDockWidget(self, widget: QtWidgets.QDockWidget):
        widget.setParent(self)
        widget.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea)
        self.docker.addDockWidget(QtCore.Qt.LeftDockWidgetArea, widget)
    
    def collapse(self):
        children = self.findChildren(QtWidgets.QDockWidget)
        for child in children:
            child.setHidden(True)