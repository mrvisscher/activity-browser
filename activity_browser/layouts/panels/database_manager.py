# -*- coding: utf-8 -*-
from PySide2 import QtCore, QtWidgets

from ...ui.style import header
from ...ui.icons import qicons
from ...ui.tables import (DatabasesTable)
from ...signals import signals

from .panel import ABPanel
from .database import Database_Panel

class Database_Manager_Panel(ABPanel):
    def __init__(self):
        super().__init__("Databases")
        self.table = DatabasesTable()
        self.table.setToolTip("To select a database, double-click on an entry")

        # Temporary inclusion to explain things before checkbox is back
        self.label_change_readonly = QtWidgets.QLabel(
            "To change a database from read-only to editable and back," +
            " click on the checkbox in the table."
        )
        self.label_change_readonly.setWordWrap(True)

        # Buttons & Actions
        self.add_default_data_button = QtWidgets.QPushButton(
            qicons.import_db, "Add default data (biosphere flows and impact categories)"
        )
        self.new_database_action = QtWidgets.QAction("New database", self)
        self.import_database_action = QtWidgets.QAction("Import database", self)

        self._construct_layout()
        self._connect_signals()

    def _connect_signals(self):
        self.add_default_data_button.clicked.connect(signals.install_default_data.emit)
        self.import_database_action.triggered.connect(signals.import_database.emit)
        self.new_database_action.triggered.connect(signals.add_database.emit)

        signals.project_selected.connect(self.update_widget)
        signals.database_selected.connect(self.open_or_focus_database)

    def _construct_layout(self):
        # setup overall Layout
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignTop)
        layout.addWidget(self.add_default_data_button)
        layout.addWidget(self.table)
        layout.addWidget(self.label_change_readonly)

        # setup the menubar
        self.menubar = QtWidgets.QMenuBar(self)
        self.menubar.addAction(self.new_database_action)
        self.menubar.addAction(self.import_database_action)
        layout.setMenuBar(self.menubar)

        return self.setLayout(layout)

    def update_widget(self):
        no_databases = self.table.rowCount() == 0
        self.add_default_data_button.setVisible(no_databases)

        self.menubar.setVisible(not no_databases)
        self.table.setVisible(not no_databases)
        self.label_change_readonly.setVisible(not no_databases)
    
    def open_or_focus_database(self, db_name: str):
        docker = self.parent().parent()

        # put focus if the database is already open
        existing_panel: Database_Panel = docker.findChild(Database_Panel, db_name)
        if existing_panel: return existing_panel.parent().raise_() 

        database_panel = Database_Panel(db_name)
        database_panel.setObjectName(db_name)
        database_panel.table.model.sync(db_name)

        database_panel.dock_widget.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        first_relative: QtWidgets.QDockWidget = docker.findChild(Database_Panel)
        docker.addDockWidget(QtCore.Qt.LeftDockWidgetArea, database_panel.dock_widget)
        if first_relative: docker.tabifyDockWidget(first_relative.dock_widget, database_panel.dock_widget)