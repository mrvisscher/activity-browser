from logging import getLogger

import pandas as pd
from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Signal, SignalInstance

import bw2data as bd

from activity_browser import actions, ui, project_settings, application, signals
from activity_browser.ui import core
from activity_browser.bwutils import AB_metadata

log = getLogger(__name__)


DEFAULT_STATE = {
    "columns": ["Activity", "Product", "Type", "Unit", "Location"],
    "visible_columns": ["Activity", "Product", "Type", "Unit", "Location"],
}


NODETYPES = {
    "all_nodes": [],
    "processes": ["process", "multifunctional", "processwithreferenceproduct", "nonfunctional"],
    "products": ["product", "processwithreferenceproduct", "waste"],
    "biosphere": ["natural resource", "emission", "inventory indicator", "economic", "social"],
}


class DatabaseProductViewer(QtWidgets.QWidget):

    def __init__(self, parent, db_name: str):
        super().__init__(parent)
        self.database = bd.Database(db_name)
        self.model = ProductModel(self)

        # Create the QTableView and set the model
        self.table_view = ProductView(self)
        self.table_view.setModel(self.model)
        self.table_view.restoreSate(self.get_state_from_settings(), self.build_df())

        self.search = QtWidgets.QLineEdit(self)
        self.search.setMaximumHeight(30)
        self.search.setPlaceholderText("Quick Search")

        self.search.textChanged.connect(self.table_view.setAllFilter)

        table_layout = QtWidgets.QHBoxLayout()
        table_layout.setSpacing(0)
        table_layout.addWidget(self.table_view)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.search)
        layout.addLayout(table_layout)

        # Set the table view as the central widget of the window
        self.setLayout(layout)

        # connect signals
        signals.database.deleted.connect(self.deleteLater)
        AB_metadata.synced.connect(self.sync)
        self.table_view.query_changed.connect(self.search_error)

    def sync(self):
        self.model.setDataFrame(self.build_df())

    def build_df(self) -> pd.DataFrame:
        full_df = AB_metadata.get_database_metadata(self.database.name)

        expected = ["processor", "product", "type", "unit", "location"]
        for column_name in expected:
            if column_name not in full_df.columns:
                full_df[column_name] = None

        with_processor = full_df[full_df.processor.isin(full_df.key)].copy()
        with_processor["process_name"] = full_df.loc[with_processor.processor].set_index(with_processor.index).name
        with_processor["process_id"] = full_df.loc[with_processor.processor].set_index(with_processor.index).id

        no_processor = full_df[full_df.processor.isin(full_df.key) == False].copy()
        no_processor.drop(no_processor[no_processor.key.isin(with_processor.processor)].index, inplace=True)
        no_processor.drop(no_processor[no_processor.type == "readonly_process"].index, inplace=True)

        final = pd.DataFrame({
            "Activity": list(with_processor["process_name"]) + list(no_processor["name"]),
            "Product": list(with_processor["name"]) + list(no_processor["product"]),
            "Type": list(with_processor["type"]) + list(no_processor["type"]),
            "Unit": list(with_processor["unit"]) + list(no_processor["unit"]),
            "Location": list(with_processor["location"]) + list(no_processor["location"]),
            "Product Key": list(with_processor["key"]) + [None] * len(no_processor),
            "Product ID": list(with_processor["id"]) + [None] * len(no_processor),
            "Activity Key": list(with_processor["processor"]) + list(no_processor["key"]),
            "Activity ID": list(with_processor["process_id"]) + list(no_processor["id"]),
        })

        return final

    def event(self, event):
        if event.type() == QtCore.QEvent.Type.DeferredDelete:
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


class ProductView(ui.widgets.ABTreeView):
    query_changed: SignalInstance = Signal(bool)

    class ContextMenu(ui.widgets.ABTreeView.ContextMenu):
        def __init__(self, pos, view: "ProductView"):
            super().__init__(pos, view)

            self.activity_open = actions.ActivityOpen.get_QAction(view.selected_activities)
            self.activity_graph = actions.ActivityGraph.get_QAction(view.selected_activities)
            self.process_new = actions.ActivityNewProcess.get_QAction(view.parent().database.name)
            self.activity_delete = actions.ActivityDelete.get_QAction(view.selected_products)
            # self.activity_relink = actions.ActivityRelink.get_QAction(view.selected_processes)

            # self.activity_duplicate = actions.ActivityDuplicate.get_QAction(view.selected_products)
            # self.activity_duplicate_to_loc = actions.ActivityDuplicateToLoc.get_QAction(
            #     view.selected_products[0] if view.selected_products else None)
            # self.activity_duplicate_to_db = actions.ActivityDuplicateToDB.get_QAction(view.selected_keys)

            self.copy_sdf = QtWidgets.QAction(ui.icons.qicons.superstructure,
                                              "Exchanges for scenario difference file", None)

            if view.indexAt(pos).row() == -1:
                self.init_none()
                return

            self.addAction(self.activity_open)
            self.addAction(self.activity_graph)
            self.addAction(self.process_new)
            #self.addMenu(self.duplicates_menu())
            self.addAction(self.activity_delete)
            #self.addAction(self.activity_relink)
            self.addMenu(self.copy_menu())

            if len(view.selected_products) == 1:
                self.init_single()
            else:
                self.init_multiple()

        def init_none(self):
            self.addAction(self.process_new)

        def init_single(self):
            self.activity_open.setText("Open process")
            self.activity_graph.setText("Open process in Graph Explorer")
            # self.activity_duplicate.setText("Duplicate product")
            self.activity_delete.setText("Delete product")

        def init_multiple(self):
            self.activity_open.setText("Open processes")
            self.activity_graph.setText("Open processes in Graph Explorer")
            # self.activity_duplicate.setText("Duplicate products")
            self.activity_delete.setText("Delete products")

            # self.activity_duplicate_to_loc.setEnabled(False)
            # self.activity_relink.setEnabled(False)

        def duplicates_menu(self):
            menu = QtWidgets.QMenu(self)

            menu.setTitle("Duplicate products")
            menu.setIcon(ui.icons.qicons.copy)

            menu.addAction(self.activity_duplicate)
            menu.addAction(self.activity_duplicate_to_loc)
            menu.addAction(self.activity_duplicate_to_db)
            return menu

        def copy_menu(self):
            menu = QtWidgets.QMenu(self)

            menu.setTitle("Copy to clipboard")
            menu.setIcon(ui.icons.qicons.copy_to_clipboard)

            menu.addAction(self.copy_sdf)
            return menu

    def __init__(self, parent: DatabaseProductViewer):
        super().__init__(parent)
        self.setSortingEnabled(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QTableView.DragDropMode.DragOnly)
        self.setSelectionBehavior(ui.widgets.ABTreeView.SelectionBehavior.SelectRows)
        self.setSelectionMode(ui.widgets.ABTreeView.SelectionMode.ExtendedSelection)

        self.allFilter = ""

    def mouseDoubleClickEvent(self, event) -> None:
        if self.selected_activities:
            actions.ActivityOpen.run(self.selected_activities)

    def setAllFilter(self, query: str):
        self.allFilter = query
        try:
            self.applyFilter()
            self.query_changed.emit(True)
        except Exception as e:
            print(f"Error in query: {type(e).__name__}: {e}")
            self.query_changed.emit(False)

    def buildQuery(self) -> str:
        node_query = ""

        if self.allFilter.startswith('='):
            return super().buildQuery() + f" & ({self.allFilter[1:]})" + node_query

        col_names = [self.model().columns[i] for i in range(1, len(self.model().columns)) if not self.isColumnHidden(i)]

        q = " | ".join([f"(`{col}`.astype('str').str.contains('{self.format_query(self.allFilter)}'))" for col in col_names])
        return super().buildQuery() + f" & ({q})" + node_query if q else super().buildQuery() + node_query

    @property
    def selected_products(self) -> [tuple]:
        items = [i.internalPointer() for i in self.selectedIndexes() if isinstance(i.internalPointer(), ProductItem)]
        return list({item["Product Key"] for item in items if item["Product Key"] is not None})

    @property
    def selected_activities(self) -> [tuple]:
        items = [i.internalPointer() for i in self.selectedIndexes() if isinstance(i.internalPointer(), ProductItem)]
        return list({item["Activity Key"] for item in items if item["Activity Key"] is not None})


class ProductModel(ui.widgets.ABAbstractItemModel):

    def createItems(self, dataframe=None) -> list[ui.widgets.ABDataItem]:
        items = []
        for index, data in dataframe.to_dict(orient="index").items():
            items.append(ProductItem(index, data))
        return items

    def mimeData(self, indices: [QtCore.QModelIndex]):
        data = core.ABMimeData()
        data.setPickleData("application/bw-nodekeylist", self.values_from_indices("Activity key", indices))
        return data

    @staticmethod
    def values_from_indices(key: str, indices: list[QtCore.QModelIndex]):
        values = []
        for index in indices:
            item = index.internalPointer()
            if not item or item[key] is None:
                continue
            values.append(item[key])
        return values


class ProductItem(ui.widgets.ABDataItem):
    def decorationData(self, col, key):
        if key == "Activity" and self["Activity"]:
            if self["Type"] == "processwithreferenceproduct":
                return ui.icons.qicons.processproduct
            if self["Type"] in NODETYPES["biosphere"]:
                return ui.icons.qicons.biosphere
            return ui.icons.qicons.process
        if key == "Product":
            if self["Type"] in ["product", "processwithreferenceproduct"]:
                return ui.icons.qicons.product
            elif self["Type"] == "waste":
                return ui.icons.qicons.waste

