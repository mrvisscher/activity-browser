# -*- coding: utf-8 -*-
from PySide2 import QtCore, QtWidgets

from .panel import ABPanel
from ...signals import signals
from ...ui.icons import qicons
from ...ui.style import header
from ...ui.tables import  MethodsTable, MethodsTree



class Impact_Categories_Panel(ABPanel):
    def __init__(self):
        super().__init__("Impact Categories")

        self.tree = MethodsTree(self)
        self.tree.setToolTip(
            "Drag (groups of) impact categories to the calculation setup")
        self.table = MethodsTable(self)
        self.table.setToolTip(
            "Drag (groups of) impact categories to the calculation setup")

        # auto-search
        self.debounce_search = QtCore.QTimer()
        self.debounce_search.setInterval(300)
        self.debounce_search.setSingleShot(True)
        self.debounce_search.timeout.connect(self.set_search_term)

        #
        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setPlaceholderText("Search impact categories")
        self.search_box.setToolTip("If a large number of matches is found the\n"
                                   "tree is not expanded automatically.")
        self.search_button = QtWidgets.QToolButton()
        self.search_button.setIcon(qicons.search)
        self.search_button.setToolTip("Search impact categories.\n"
                                      "If a large number of matches is found the\n"
                                      "tree is not expanded automatically.")
        self.reset_search_button = QtWidgets.QToolButton()
        self.reset_search_button.setIcon(qicons.delete)
        self.reset_search_button.setToolTip("Clear the search")
        #
        self.mode_radio_tree = QtWidgets.QRadioButton("Tree view")
        self.mode_radio_tree.setChecked(True)
        self.mode_radio_tree.setToolTip(
            "Tree view of impact categories\n"
            "v CML 2001\n"
            "    v climate change\n"
            "        CML 2001, climate change, GWP 100a\n"
            "        ...\n"
            "You can drag entire 'branches' of impact categories at once")
        #
        self.mode_radio_list = QtWidgets.QRadioButton("List view")
        self.mode_radio_list.setToolTip(
            "List view of impact categories")
        #
        search_layout = QtWidgets.QHBoxLayout()
        search_layout.addWidget(self.search_box)
        search_layout.addWidget(self.search_button)
        search_layout.addWidget(self.reset_search_button)
        #
        mode_layout = QtWidgets.QHBoxLayout()
        mode_layout.setAlignment(QtCore.Qt.AlignTop)
        mode_layout.addWidget(header('Impact Categories'))
        search_layout.addWidget(self.mode_radio_tree)
        search_layout.addWidget(self.mode_radio_list)
        #
        mode_layout_container = QtWidgets.QWidget()
        mode_layout_container.setLayout(mode_layout)
        #
        search_layout_container = QtWidgets.QWidget()
        search_layout_container.setLayout(search_layout)
        #
        container = QtWidgets.QVBoxLayout()
        container.setAlignment(QtCore.Qt.AlignTop)
        container.addWidget(mode_layout_container)
        container.addWidget(search_layout_container)
        container.addWidget(self.tree)
        container.addWidget(self.table)
        self.table.setVisible(False)
        self.setLayout(container)

        self.connect_signals()

    def connect_signals(self):
        self.mode_radio_list.toggled.connect(self.update_view)

        self.reset_search_button.clicked.connect(self.table.sync)
        self.reset_search_button.clicked.connect(self.tree.model.sync)

        self.search_button.clicked.connect(self.set_search_term)
        self.search_button.clicked.connect(self.set_search_term)
        self.search_box.returnPressed.connect(self.set_search_term)
        self.search_box.returnPressed.connect(self.set_search_term)
        self.search_box.textChanged.connect(self.debounce_search.start)

        self.reset_search_button.clicked.connect(self.search_box.clear)
        signals.project_selected.connect(self.search_box.clear)

    def update_view(self, toggled: bool):
        self.tree.setVisible(not toggled)
        self.table.setVisible(toggled)

    def set_search_term(self):
        search_term = self.search_box.text().strip()
        self.table.sync(query=search_term)
        self.tree.model.sync(query=search_term)