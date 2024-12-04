import re
from qtpy import QtWidgets, QtCore, QtGui

from .abstractitemmodel import ABAbstractItemModel


class ABTreeView(QtWidgets.QTreeView):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setUniformRowHeights(True)

        header = self.header()
        header.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self.header_popup)

        self.expanded_paths = set()
        self.expanded.connect(lambda index: self.expanded_paths.add(tuple(index.internalPointer().path)))
        self.collapsed.connect(lambda index: self.expanded_paths.discard(tuple(index.internalPointer().path)))

        self.filters: dict[str, str] = {}  # dict[column_name, query] for filtering the dataframe

    def setModel(self, model):
        if not isinstance(model, ABAbstractItemModel):
            raise TypeError("Model must be an instance of ABAbstractItemModel")
        super().setModel(model)

        self.setColumnHidden(0, True)
        model.grouped.connect(lambda groups: self.setColumnHidden(0, not groups))
        model.grouped.connect(lambda groups: self.expanded_paths.clear() if not groups else None)
        model.modelReset.connect(self.expand_after_reset)

    def model(self) -> ABAbstractItemModel:
        return super().model()

    def filter(self, column_name: str, query: str):
        if query:
            self.filters[column_name] = query
            self.model().filtered_columns.add(self.model().columns.index(column_name))
        elif column_name in self.filters:
            del self.filters[column_name]
            self.model().filtered_columns.discard(self.model().columns.index(column_name))
        self.applyFilter()

    def applyFilter(self, extended_query: str = ""):
        pandas_query = " & ".join([f"({col}.astype('str').str.contains('{self.format_query(q)}'))" for col, q in self.filters.items()])
        pandas_query = "(index == index)" if not pandas_query else pandas_query
        self.model().query(pandas_query + extended_query)

    @staticmethod
    def format_query(query: str) -> str:
        return query.translate(str.maketrans({'(': '\\(', ')': '\\)', "'": "\\'"}))

    def saveState(self) -> dict:
        if not self.model():
            return {}

        return {
            "columns": self.model().columns,
            "grouped_columns": [self.model().columns[i] for i in self.model().grouped_columns],
            "current_query": self.model().current_query,

            "expanded_paths": list(self.expanded_paths),
            "visible_columns": [self.model().columns[i] for i in range(len(self.model().columns)) if not self.isColumnHidden(i)],
            "filters": self.filters,

            "header_state": bytearray(self.header().saveState()).hex()
        }

    def restoreSate(self, state: dict) -> bool:
        if not self.model():
            return False

        columns = [col for col in state.get("columns", []) if col in self.model().columns]
        columns = columns + [col for col in self.model().columns if col not in columns]

        self.model().beginResetModel()
        self.model().columns = columns
        self.model().grouped_columns = [columns.index(name) for name in state.get("grouped_columns", [])]
        self.model().current_query = state.get("current_query", "")
        self.model().endResetModel()

        self.expanded_paths = set(tuple(p) for p in state.get("expanded_paths", []))
        self.filters = state.get("filters", {})
        for column_name in self.filters:
            self.model().filtered_columns.add(self.model().columns.index(column_name))

        for col_name in [col for col in columns if col not in state.get("visible_columns", columns)]:
            self.setColumnHidden(columns.index(col_name), True)

        self.header().restoreState(bytearray.fromhex(state.get("header_state", "")))

        return True

    def expand_after_reset(self):
        indices = []
        for path in self.expanded_paths:
            try:
                indices.append(self.model().indexFromPath(list(path)))
            except KeyError:
                continue

        for index in indices:
            self.expand(index)

    def header_popup(self, pos: QtCore.QPoint):
        col = self.columnAt(pos.x())
        if col == 0:
            menu = self.group_col_menu()
        else:
            menu = self.col_menu(col)
        menu.exec_(self.mapToGlobal(pos))

    def col_menu(self, column: int):
        menu = QtWidgets.QMenu(self)
        col_name = self.model().columns[column]

        search_box = QtWidgets.QLineEdit(menu)
        search_box.setText(self.filters.get(col_name, ""))
        search_box.setPlaceholderText("Search")
        search_box.selectAll()

        search_box.textChanged.connect(lambda query: self.filter(col_name, query))
        widget_action = QtWidgets.QWidgetAction(menu)
        widget_action.setDefaultWidget(search_box)
        menu.addAction(widget_action)

        menu.addAction(
            QtGui.QIcon(),
            "Group by column",
            lambda: self.model().group(column),
        )
        menu.addAction(
            QtGui.QIcon(),
            "Clear column filter",
            lambda: self.filter(col_name, ""),
        )
        menu.addAction(
            QtGui.QIcon(),
            "Clear all filters",
            lambda: [self.filter(name, "") for name in list(self.filters.keys())],
        )
        menu.addSeparator()
        menu.addMenu(self.view_menu())

        search_box.setFocus()
        return menu

    def group_col_menu(self):
        menu = QtWidgets.QMenu(self)
        menu.addAction(
            QtGui.QIcon(),
            "Ungroup",
            self.model().ungroup,
        )
        return menu

    def view_menu(self) -> QtWidgets.QMenu:

        def toggle_slot(action: QtWidgets.QAction):
            index = action.data()
            hidden = self.isColumnHidden(index)
            self.setColumnHidden(index, not hidden)

        menu = QtWidgets.QMenu(self)
        menu.setTitle("View")
        self.view_actions = []

        for i in range(1, len(self.model().columns)):
            action = QtWidgets.QAction(self.model().columns[i])
            action.setCheckable(True)
            action.setChecked(not self.isColumnHidden(i))
            action.setData(i)
            menu.addAction(action)
            self.view_actions.append(action)

        menu.triggered.connect(toggle_slot)

        return menu
