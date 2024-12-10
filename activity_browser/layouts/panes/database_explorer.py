import re

from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Signal, SignalInstance

from activity_browser import actions, ui, project_settings, application
from activity_browser.ui import core
from activity_browser.bwutils import AB_metadata
from activity_browser.mod import bw2data as bd

DEFAULT_STATE = {
    "columns": ["", "name", "activity", "activity type", "location", "unit"],
    "visible_columns": ["name", "activity", "activity type", "location", "unit"],
}


class DatabaseExplorer(QtWidgets.QWidget):
    def __init__(self, parent, db_name: str):
        super().__init__(parent)
        self.database = bd.Database(db_name)
        self.model = NodeModel(self)

        # Create the QTableView and set the model
        self.table_view = NodeView(self)
        self.table_view.setModel(self.model)
        self.model.setDataFrame(AB_metadata.get_database_metadata(db_name))
        self.table_view.restoreSate(self.get_state_from_settings())

        self.search = QtWidgets.QLineEdit(self)
        self.search.setMaximumHeight(30)
        self.search.setPlaceholderText("Quick Search")

        self.search.textChanged.connect(self.table_view.filter_all)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.search)
        layout.addWidget(self.table_view)

        # Set the table view as the central widget of the window
        self.setLayout(layout)

        # connect signals
        self.database.changed.connect(self.database_changed)
        self.database.deleted.connect(self.deleteLater)
        self.table_view.query_changed.connect(self.search_error)

    def database_changed(self, database: bd.Database) -> None:
        if database.name != self.database.name:  # only update if the database changed is the one shown by this widget
            return

        self.model.setDataFrame(AB_metadata.get_database_metadata(database.name))

    def event(self, event):
        if event.type() == QtCore.QEvent.DeferredDelete:
            self.save_state_to_settings()

        return super().event(event)

    def save_state_to_settings(self):
        project_settings.settings["database_explorer"] = project_settings.settings.get("database_explorer", {})
        project_settings.settings["database_explorer"][self.database.name] = self.table_view.saveState()
        project_settings.write_settings()

    def get_state_from_settings(self):
        return project_settings.settings.get("database_explorer", {}).get(self.database.name, DEFAULT_STATE)

    def search_error(self, reset=False):
        if reset:
            self.search.setPalette(application.palette())
            return

        palette = self.search.palette()
        palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(255, 128, 128))
        self.search.setPalette(palette)


class NodeView(ui.widgets.ABTreeView):
    query_changed: SignalInstance = Signal(bool)

    def __init__(self, parent: DatabaseExplorer):
        super().__init__(parent)
        self.setSortingEnabled(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QTableView.DragOnly)
        self.setSelectionBehavior(ui.widgets.ABTreeView.SelectRows)
        self.setSelectionMode(ui.widgets.ABTreeView.MultiSelection)

    def contextMenuEvent(self, event) -> None:
        """Construct and present a menu."""
        if self.indexAt(event.pos()).row() == -1:
            menu = NodeViewContextMenu.init_none(self)
        else:
            menu = NodeViewContextMenu.init_single(self)
        menu.exec_(event.globalPos())

    def mouseDoubleClickEvent(self, event) -> None:
        if self.selected_keys:
            actions.ActivityOpen.run(self.selected_keys)

    def filter_all(self, query: str):
        # go to advanced querying if the query starts with the equal sign
        if query.startswith('='):
            return self.query_filter(query[1:])

        col_names = [self.model().columns[i] for i in range(1, len(self.model().columns)) if not self.isColumnHidden(i)]

        pandas_query = " | ".join([f"(`{col}`.astype('str').str.contains('{self.format_query(query)}'))" for col in col_names])
        pandas_query = " & " + pandas_query if pandas_query else ""
        self.applyFilter(pandas_query)
        self.query_changed.emit(True)

    def query_filter(self, query: str) -> bool:
        try:
            self.applyFilter(f" & ({query})")
            self.query_changed.emit(True)
        except Exception as e:
            print(f"Error in query: {type(e).__name__}: {e}")
            self.query_changed.emit(False)

    @property
    def selected_keys(self) -> [tuple]:
        return self.model().get_keys(self.selectedIndexes())


class NodeViewContextMenu(QtWidgets.QMenu):
    def __init__(self, parent: NodeView):
        super().__init__(parent)

        self.activity_open = actions.ActivityOpen.get_QAction(parent.selected_keys)
        self.activity_graph = actions.ActivityGraph.get_QAction(parent.selected_keys)
        self.activity_new = actions.ActivityNew.get_QAction(parent.parent().database.name)
        self.activity_delete = actions.ActivityDelete.get_QAction(parent.selected_keys)
        self.activity_relink = actions.ActivityRelink.get_QAction(parent.selected_keys)

        self.activity_duplicate = actions.ActivityDuplicate.get_QAction(parent.selected_keys)
        self.activity_duplicate_to_loc = actions.ActivityDuplicateToLoc.get_QAction(parent.selected_keys[0] if parent.selected_keys else None)
        self.activity_duplicate_to_db = actions.ActivityDuplicateToDB.get_QAction(parent.selected_keys)

        self.copy_sdf = QtWidgets.QAction(ui.icons.qicons.superstructure, "Exchanges for scenario difference file", None)

        self.addAction(self.activity_open)
        self.addAction(self.activity_graph)
        self.addAction(self.activity_new)
        self.addMenu(self.duplicates_menu())
        self.addAction(self.activity_delete)
        self.addAction(self.activity_relink)
        self.addMenu(self.copy_menu())

    @classmethod
    def init_none(cls, parent: NodeView):
        menu = cls(parent)

        menu.clear()
        menu.addAction(menu.activity_new)

        return menu

    @classmethod
    def init_single(cls, parent: NodeView):
        menu = cls(parent)

        menu.activity_open.setText(f"Open activity")
        menu.activity_graph.setText(f"Open activity in Graph Explorer")
        menu.activity_duplicate.setText(f"Duplicate activity")
        menu.activity_delete.setText(f"Delete activity")

        return menu

    @classmethod
    def init_multiple(cls, parent: NodeView):
        menu = cls(parent)

        menu.activity_open.setText(f"Open activities")
        menu.activity_graph.setText(f"Open activities in Graph Explorer")
        menu.activity_duplicate.setText(f"Duplicate activities")
        menu.activity_delete.setText(f"Delete activities")

        menu.activity_duplicate_to_loc.setEnabled(False)
        menu.activity_relink.setEnabled(False)

        return menu

    def duplicates_menu(self):
        menu = QtWidgets.QMenu(self)

        menu.setTitle(f"Duplicate activities")
        menu.setIcon(ui.icons.qicons.copy)

        menu.addAction(self.activity_duplicate)
        menu.addAction(self.activity_duplicate_to_loc)
        menu.addAction(self.activity_duplicate_to_db)
        return menu

    def copy_menu(self):
        menu = QtWidgets.QMenu(self)

        menu.setTitle(f"Copy to clipboard")
        menu.setIcon(ui.icons.qicons.copy_to_clipboard)

        menu.addAction(self.copy_sdf)
        return menu


class NodeModel(ui.widgets.ABAbstractItemModel):

    def mimeData(self, indices: [QtCore.QModelIndex]):
        data = core.ABMimeData()
        data.setPickleData("application/bw-nodekeylist", self.get_keys(indices))
        return data

    def get_keys(self, indices: [QtCore.QModelIndex]):
        keys = []
        for index in indices:
            df = self.resolveIndex(index)
            keys.extend(df["key"])
        return list(set(keys))
