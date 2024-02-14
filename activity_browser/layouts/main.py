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
from .panels import RightPanel, Database_Manager_Panel , Impact_Categories_Panel
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
        databases_widget_bar.addPanel(Database_Manager_Panel())
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, databases_widget_bar)

        ic_widget_bar = WidgetBar("Impact Categories", self)
        ic_widget_bar.addPanel(Impact_Categories_Panel())
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, ic_widget_bar)
        self.tabifyDockWidget(databases_widget_bar, ic_widget_bar)


        parameters_widget_bar = WidgetBar("Parameters", self)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, parameters_widget_bar)
        self.tabifyDockWidget(databases_widget_bar, parameters_widget_bar)

        scenarios_widget_bar = WidgetBar("Scenarios", self)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, scenarios_widget_bar)
        self.tabifyDockWidget(databases_widget_bar, scenarios_widget_bar)

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

        #self.tabifiedDockWidgetActivated.connect(self.dockwidget_sizing)

    def dockwidget_sizing(self, widget: QtWidgets.QDockWidget):
        area = self.dockWidgetArea(widget)
        menubars: list[WidgetBar] = self.findChildren(WidgetBar)
        for bar in menubars:
            if bar == widget: continue
            if self.dockWidgetArea(bar) != area: continue
            bar.docker.collapse()
        widget.docker.expand()


    def toggle_debug_window(self):
        """Toggle the bottom debug window"""
        menubars = self.findChildren(WidgetBar)
        for bar in menubars:
            bar.docker.collapse()

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
        # as little stuff as possible
        self.setFeatures(self.NoDockWidgetFeatures)
        self.setTitleBarWidget(QtWidgets.QWidget())

        # initialize docker
        self.docker = Docker(self)
        self.setWidget(self.docker)        
      
    def addPanel(self, panel: QtWidgets.QWidget):
        """Easy method to put a widget in this docker area"""
        dock_widget = panel.dock_widget

        dock_widget.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea)
        self.docker.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock_widget)
        self.docker.sync_width()
    
class Docker(QtWidgets.QMainWindow):
    collapsed = True

    def __init__(self, parent):
        super().__init__(None)
        self.spacer = self.generate_spacer()

        self.setTabPosition(QtCore.Qt.AllDockWidgetAreas, QtWidgets.QTabWidget.North)
        self.setMinimumSize(1, 1)

        self.setMinimumWidth(200)
        self.setMaximumWidth(400)

        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.spacer)
        self.sync_spacer()
    
    def generate_spacer(self):
        spacer_widget = QtWidgets.QWidget()
        spacer_widget.setFixedHeight(1)

        spacer = QtWidgets.QDockWidget("spacer", self)
        spacer.setWidget(spacer_widget)
        spacer.setTitleBarWidget(QtWidgets.QWidget())
        spacer.setFixedHeight(1)
        return spacer

    def addDockWidget(self, area, dock_widget):
        dock_widget.topLevelChanged.connect(lambda x: self.sync_spacer())
        dock_widget.destroyed.connect(self.sync_spacer)
        super().addDockWidget(area, dock_widget)
        self.sync_spacer()
         
    def sync_spacer(self):
        children = self.findChildren(QtWidgets.QDockWidget)
        docked = [child for child in children if not child.isFloating() and child != self.spacer]

        #print(f"Toggling spacer | Docked widgets = {len(docked)}")

        if len(docked) == 0:
            print("adding spacer")
            self.spacer.setHidden(False)
            self.setDockOptions(self.AnimatedDocks)
        if len(docked) >= 1:
            print("removing spacer")
            #self.removeDockWidget(self.spacer)
            self.spacer.setHidden(True)
            self.setDockOptions(self.AnimatedDocks | self.AllowTabbedDocks)
          
    
    def sync_width(self):
        return
        children = self.findChildren(QtWidgets.QDockWidget)
        docked = [child for child in children if not child.isFloating() and not child.isHidden()]


        
        self.sync_spacer()

        if self.collapsed:
            self.setMinimumWidth(0)
            self.setMaximumWidth(500)
            return

        children = self.findChildren(QtWidgets.QDockWidget)
        docked = [child for child in children if not child.isFloating() and not child.isHidden()]

        min_width = 0
        max_width = 500

        for child in docked:
            child_min_width = child.minimumWidth()
            child_max_width = child.maximumWidth()
            if min_width < child_min_width: min_width = child_min_width
            if max_width > child_max_width: max_width = child_max_width
            
        self.setMinimumWidth(min_width)
        self.setMaximumWidth(max_width)
        #print(f"Sync width for {self.parent().windowTitle()}: {min_width=} {max_width=}")
