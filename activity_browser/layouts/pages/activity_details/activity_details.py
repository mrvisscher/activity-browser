from logging import getLogger

import pandas as pd
import numpy as np
from peewee import DoesNotExist

from qtpy import QtCore, QtWidgets
from qtpy.QtCore import Qt

import bw2data as bd

from activity_browser import project_settings, signals
from activity_browser.bwutils import AB_metadata

from activity_browser.ui.icons import qicons
from activity_browser.ui.style import style_activity_tab
from activity_browser.ui.widgets import (
    ActivityDataGrid,
    SignalledPlainTextEdit,
    TagEditor,
)

from .views import ExchangeView
from .models import ExchangeModel

log = getLogger(__name__)

NODETYPES = {
    "processes": ["process", "multifunctional", "processwithreferenceproduct", "nonfunctional"],
    "products": ["product", "processwithreferenceproduct", "waste"],
    "biosphere": ["natural resource", "emission", "inventory indicator", "economic", "social"],
}

EXCHANGE_MAP = {
    "natural resource": "biosphere", "emission": "biosphere", "inventory indicator": "biosphere",
    "economic": "biosphere", "social": "biosphere", "product": "technosphere",
    "processwithreferenceproduct": "technosphere", "waste": "technosphere",
}


class ActivityDetails(QtWidgets.QWidget):
    _populate_later_flag = False

    def __init__(self, key: tuple, read_only=True, parent=None):
        super().__init__(parent)
        self.read_only = read_only
        self.db_read_only = project_settings.db_is_readonly(db_name=key[0])
        self.key = key
        self.db_name = key[0]
        self.activity = bd.get_activity(key)
        self.database = bd.Database(self.db_name)

        # Edit Activity checkbox
        self.checkbox_edit_act = QtWidgets.QCheckBox("Edit Activity")
        self.checkbox_edit_act.setChecked(not self.read_only)
        self.checkbox_edit_act.toggled.connect(lambda checked: self.act_read_only_changed(not checked))

        # Activity Description
        self.activity_description = SignalledPlainTextEdit(
            key=key,
            field="comment",
            parent=self,
        )

        # Activity Description checkbox
        self.checkbox_activity_description = QtWidgets.QCheckBox(
            "Description", parent=self
        )
        self.checkbox_activity_description.clicked.connect(
            self.toggle_activity_description_visibility
        )
        self.checkbox_activity_description.setChecked(not self.read_only)
        self.checkbox_activity_description.setToolTip(
            "Show/hide the activity description"
        )
        self.toggle_activity_description_visibility()

        # Reveal/hide uncertainty columns
        self.checkbox_uncertainty = QtWidgets.QCheckBox("Uncertainty")
        self.checkbox_uncertainty.setToolTip("Show/hide the uncertainty columns")
        self.checkbox_uncertainty.setChecked(False)

        # Reveal/hide exchange comment columns
        self.checkbox_comment = QtWidgets.QCheckBox("Comments")
        self.checkbox_comment.setToolTip("Show/hide the comment column")
        self.checkbox_comment.setChecked(False)

        # Tags button
        self.tags_button = QtWidgets.QPushButton("Tags")
        self.tags_button.clicked.connect(self.open_tag_editor)
        self.tags_button.setToolTip("Show the tags dialog")

        # Toolbar Layout
        toolbar = QtWidgets.QToolBar()
        self.graph_action = toolbar.addAction(
            qicons.graph_explorer, "Show in Graph Explorer", self.open_graph
        )
        toolbar.addWidget(self.checkbox_edit_act)
        toolbar.addWidget(self.checkbox_activity_description)
        toolbar.addWidget(self.checkbox_uncertainty)
        toolbar.addWidget(self.checkbox_comment)
        toolbar.addWidget(self.tags_button)

        # Activity information
        # this contains: activity name, location, database
        self.activity_data_grid = ActivityDataGrid(
            read_only=self.read_only, parent=self
        )
        self.db_read_only_changed(db_name=self.db_name, db_read_only=self.db_read_only)

        # Exchanges
        self.output_view = ExchangeView(self)
        self.output_model = ExchangeModel(self)
        self.output_view.setModel(self.output_model)

        self.input_view = ExchangeView(self)
        self.input_model = ExchangeModel(self)
        self.input_view.setModel(self.input_model)

        # Full layout
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(10, 10, 4, 1)
        layout.setAlignment(QtCore.Qt.AlignTop)

        layout.addWidget(toolbar)
        layout.addWidget(self.activity_data_grid)
        layout.addWidget(self.activity_description)
        layout.addWidget(QtWidgets.QLabel("<b>Output:</b>"))
        layout.addWidget(self.output_view)
        layout.addWidget(QtWidgets.QLabel("<b>Input:</b>"))
        layout.addWidget(self.input_view)

        self.setLayout(layout)

        self.populate()
        self.update_tooltips()
        self.update_style()
        self.connect_signals()

        # Make the activity tab editable in case it's new
        if not self.read_only:
            self.act_read_only_changed(False)

    def connect_signals(self):
        signals.database_read_only_changed.connect(self.db_read_only_changed)

        signals.node.deleted.connect(self.on_node_deleted)
        signals.database.deleted.connect(self.on_database_deleted)

        signals.node.changed.connect(self.populateLater)
        signals.edge.changed.connect(self.populateLater)
        # signals.edge.deleted.connect(self.populate)

        signals.meta.databases_changed.connect(self.populateLater)

        signals.parameter.recalculated.connect(self.populateLater)

    def on_node_deleted(self, node):
        if node.id == self.activity.id:
            self.deleteLater()

    def on_database_deleted(self, name):
        if name == self.activity["database"]:
            self.deleteLater()

    def open_graph(self) -> None:
        signals.open_activity_graph_tab.emit(self.key)

    def populateLater(self):
        def slot():
            self._populate_later_flag = False
            self.populate()

        if self._populate_later_flag:
            return

        self.thread().eventDispatcher().awake.connect(slot, Qt.ConnectionType.SingleShotConnection)
        self._populate_later_flag = True

    def populate(self) -> None:
        """Populate the various tables and boxes within the Activity Detail tab"""
        if self.db_name in bd.databases:
            # Avoid a weird signal interaction in the tests
            try:
                self.activity = bd.get_activity(self.key)  # Refresh activity.
            except DoesNotExist:
                signals.close_activity_tab.emit(self.key)
                return
        self.populate_description_box()

        # update the object name to be the activity name
        self.setObjectName(self.activity["name"])

        # fill in the values of the ActivityTab widgets, excluding the ActivityDataGrid which is populated separately
        production = self.activity.production()
        technosphere = self.activity.technosphere()
        biosphere = self.activity.biosphere()

        inputs = ([x for x in production if x["amount"] < 0] +
                  [x for x in technosphere if x["amount"] >= 0] +
                  [x for x in biosphere if (x.input["type"] != "emission" and x["amount"] >= 0) or (x.input["type"] == "emission" and x["amount"] < 0)])

        outputs = ([x for x in production if x["amount"] >= 0] +
                   [x for x in technosphere if x["amount"] < 0] +
                   [x for x in biosphere if (x.input["type"] == "emission" and x["amount"] >= 0) or (x.input["type"] != "emission" and x["amount"] < 0)])

        self.output_model.setDataFrame(self.build_df(outputs))
        self.input_model.setDataFrame(self.build_df(inputs))

        self.activity_data_grid.populate()

    def build_df(self, exchanges) -> pd.DataFrame:
        if not exchanges:
            return pd.DataFrame()

        exc_df = pd.DataFrame(exchanges)
        act_df = AB_metadata.get_metadata(exc_df["input"], None)
        df = pd.DataFrame({
            "Amount": list(exc_df["amount"]),
            "Unit": list(act_df["unit"]),
            "Name": list(act_df["name"]),
            "Location": list(act_df["location"]),
            "Exchange Type": list(exc_df["type"]),
            "Activity Type": list(act_df["type"]),
            "Allocation Factor": list(act_df["allocation_factor"]) if "allocation_factor" in act_df.columns else None,
            "_exchange": exchanges,
            "_activity_id": list(act_df["id"]),
            "_allocate_by": self.activity.get("default_allocation"),
        })

        if "properties" in act_df.columns:
            for i, props in act_df["properties"].reset_index(drop=True).items():
                if not isinstance(props, dict):
                    continue

                for prop, value in props.items():
                    df.loc[i, f"Property: {prop}"] = [value]  # inserted using list because Pandas is weird about setting dicts as values

        df["Formula"] = exc_df.get("formula", np.nan)

        return df

    def populate_description_box(self):
        """Populate the activity description."""
        self.activity_description.refresh_text(self.activity.get("comment", ""))
        self.activity_description.setReadOnly(self.read_only)

    def toggle_activity_description_visibility(self) -> None:
        """Show only if checkbox is checked."""
        self.activity_description.setVisible(
            self.checkbox_activity_description.isChecked()
        )

    def act_read_only_changed(self, read_only: bool) -> None:
        """When read_only=False specific data fields in the tables below become user-editable
        When read_only=True these same fields become read-only"""
        self.read_only = read_only
        self.activity_description.setReadOnly(self.read_only)

        if (
            not self.read_only
        ):  # update unique locations, units, etc. for editing (metadata)
            signals.edit_activity.emit(self.db_name)

        self.activity_data_grid.set_activity_fields_read_only(read_only=self.read_only)
        self.activity_data_grid.populate_database_combo()

        self.update_tooltips()
        self.update_style()

    def db_read_only_changed(self, db_name: str, db_read_only: bool) -> None:
        """If database of open activity is set to read-only, the read-only checkbox cannot now be unchecked by user"""
        if db_name == self.db_name:
            self.db_read_only = db_read_only

            # if activity was editable, but now the database is read-only, read_only state must be changed to false.
            if not self.read_only and self.db_read_only:
                self.checkbox_edit_act.setChecked(False)
                self.act_read_only_changed(read_only=True)

            # update checkbox to greyed-out or not
            read_only_process = self.activity.get("type") == "readonly_process"
            self.checkbox_edit_act.setEnabled(not self.db_read_only and not read_only_process)
            self.update_tooltips()

        else:  # on read-only state change for a database different to the open activity...
            # update values in database list to ensure activity cannot be duplicated to read-only db
            self.activity_data_grid.populate_database_combo()

    def update_tooltips(self) -> None:
        if self.db_read_only:
            self.checkbox_edit_act.setToolTip(
                "The database this activity belongs to is read-only."
                " Enable database editing with checkbox in databases list"
            )
        else:
            if self.read_only:
                self.checkbox_edit_act.setToolTip(
                    "Click to enable editing. Edits are saved automatically"
                )
            else:
                self.checkbox_edit_act.setToolTip(
                    "Click to prevent further edits. Edits are saved automatically"
                )

    def update_style(self) -> None:
        # pass
        if self.read_only:
            self.setStyleSheet(style_activity_tab.style_sheet_read_only)
        else:
            self.setStyleSheet(style_activity_tab.style_sheet_editable)

    def open_tag_editor(self):
        """Opens the tag editor for the current"""
        # Do not save the changes if nothing changed
        if TagEditor.edit(self.activity, self.read_only, self):
            self.activity.save()



