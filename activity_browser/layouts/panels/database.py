# -*- coding: utf-8 -*-
from PySide2 import QtCore, QtWidgets

from ...ui.style import header
from ...ui.icons import qicons
from ...ui.tables import (ActivitiesBiosphereTable)
from ...signals import signals
from .panel import ABPanel

class Database_Panel(ABPanel):
    def __init__(self, name):
        super().__init__(name)
        self.table = ActivitiesBiosphereTable(self)

        # Header widget
        self.header_widget = QtWidgets.QWidget()
        self.header_layout = QtWidgets.QHBoxLayout()
        self.header_layout.setAlignment(QtCore.Qt.AlignLeft)
        self.header_layout.setMargin(0)
        self.header_widget.setLayout(self.header_layout)

        self.setup_search()

        # Overall Layout
        self.v_layout = QtWidgets.QVBoxLayout()
        self.v_layout.setAlignment(QtCore.Qt.AlignTop)
        self.v_layout.addWidget(self.header_widget)
        self.v_layout.addWidget(self.table)
        self.setLayout(self.v_layout)

        self.table.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Maximum)
        )

    def reset_widget(self):
        self.hide()
        self.table.model.clear()

    def setup_search(self):
        # 1st search box
        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setPlaceholderText("Search")
        self.search_box.returnPressed.connect(self.set_search_term)

        # search
        self.search_button = QtWidgets.QToolButton()
        self.search_button.setIcon(qicons.search)
        self.search_button.setToolTip("Filter activities")
        self.search_button.clicked.connect(self.set_search_term)

        # reset search
        self.reset_search_button = QtWidgets.QToolButton()
        self.reset_search_button.setIcon(qicons.delete)
        self.reset_search_button.setToolTip("Clear the search")
        self.reset_search_button.clicked.connect(self.table.reset_search)
        self.reset_search_button.clicked.connect(self.search_box.clear)

        signals.project_selected.connect(self.search_box.clear)
        self.header_layout.addWidget(self.search_box)

        self.header_layout.addWidget(self.search_button)
        self.header_layout.addWidget(self.reset_search_button)

    def set_search_term(self):
        search_term = self.search_box.text()
        self.table.search(search_term)