# -*- coding: utf-8 -*-
from qtpy.QtCore import QObject, Signal, SignalInstance
from blinker import signal as blinker_signal


class NodeSignals(QObject):
    changed: SignalInstance = Signal(object, object)
    deleted: SignalInstance = Signal(object)
    database_change: SignalInstance = Signal(object, object)
    code_change: SignalInstance = Signal(object, object)


class EdgeSignals(QObject):
    changed: SignalInstance = Signal(object, object)
    deleted: SignalInstance = Signal(object)
    recalculated: SignalInstance = Signal()


class MethodSignals(QObject):
    changed: SignalInstance = Signal(object)
    deleted: SignalInstance = Signal(object)


class ParameterSignals(QObject):
    changed: SignalInstance = Signal(object, object)
    deleted: SignalInstance = Signal(object)
    recalculated: SignalInstance = Signal()


class DatabaseSignals(QObject):
    written: SignalInstance = Signal(object)
    reset: SignalInstance = Signal(object)
    deleted: SignalInstance = Signal(str)


class ProjectSignals(QObject):
    changed: SignalInstance = Signal()
    created: SignalInstance = Signal()


class MetaSignals(QObject):
    databases_changed: SignalInstance = Signal(object, object)
    methods_changed: SignalInstance = Signal(object, object)


class ABSignals(QObject):
    """Signals used for the Activity Browser should be defined here.
    While arguments can be passed to signals, it is good practice not to do this if possible.
    Every signal should have a comment (no matter how descriptive the name of the signal) that describes what a
    signal is used for and after a pipe (|), what variables are sent, if any.
    """
    node = NodeSignals()
    edge = EdgeSignals()
    method = MethodSignals()
    database = DatabaseSignals()
    project = ProjectSignals()
    meta = MetaSignals()
    parameter = ParameterSignals()

    import_project = Signal()  # Import a project
    export_project = Signal()  # Export the current project
    database_selected = Signal(str)  # This database was selected (opened) | name of database
    database_read_only_changed = Signal(str, bool)  # The read_only state of database changed | name of database, read-only state
    database_tab_open = Signal(str)  # This database tab is being viewed by user | name of database
    add_activity_to_history = Signal(tuple)
    safe_open_activity_tab = Signal(tuple)  # Open activity details tab in read-only mode | key of activity
    unsafe_open_activity_tab = Signal(tuple)  # Open activity details tab in editable mode | key of activity
    close_activity_tab = Signal(tuple)  # Close this activity details tab | key of activity
    open_activity_graph_tab = Signal(tuple)  # Open the graph-view tab | key of activity
    edit_activity = Signal(str)  # An activity in this database may now be edited | name of database
    added_parameter = Signal(str, str, str)  # This parameter has been added | name of the parameter, amount, type (project, database or activity)
    parameters_changed = Signal()  # The parameters have changed
    parameter_scenario_sync = Signal(int, object, bool)  # Synchronize this data for table | index of the table, dataframe with scenario data, include default scenario
    parameter_superstructure_built = Signal(int, object)  # Superstructure built from scenarios | index of the table, dataframe with scenario data
    set_default_calculation_setup = Signal()  # Show the default (first) calculation setup
    calculation_setup_changed = Signal()  # Calculation setup was changed
    calculation_setup_selected = Signal(str)  # This calculation setup was selected (opened) | name of calculation setup
    lca_calculation = Signal(dict)  # Generate a calculation setup | dictionary with name, type (simple/scenario) and potentially scenario data
    delete_method = Signal(tuple, str)  # Delete this method | tuple of impact category, level of tree OR the proxy
    method_selected = Signal(tuple)  # This method was selected (opened) | tuple of method
    monte_carlo_finished = Signal()  # The monte carlo calculations are finished
    new_statusbar_message = Signal(str)  # Update the statusbar this message | message
    restore_cursor = Signal()  # Restore the cursor to normal
    project_updates_available = Signal(str, int)  # Project name and number of updates available
    toggle_show_or_hide_tab = Signal(str)  # Show/Hide the tab with this name | name of tab
    show_tab = Signal(str)  # Show this tab | name of tab
    hide_tab = Signal(str)  # Hide this tab | name of tab
    hide_when_empty = Signal()  # Show/Hide tab when it has/does not have sub-tabs
    plugin_selected = Signal(str, bool)  # This plugin was/was not selected | name of plugin, selected state

    def __init__(self, parent=None):
        super().__init__(parent)

        self._connect_bw_signals()

    def _connect_bw_signals(self):
        from bw2data import signals, Method
        from bw2data.meta import databases, methods

        signals.signaleddataset_on_save.connect(self._on_signaleddataset_on_save)
        signals.signaleddataset_on_delete.connect(self._on_signaleddataset_on_delete)
        signals.on_activity_database_change.connect(self._on_activity_database_change)
        signals.on_activity_code_change.connect(self._on_activity_code_change)

        signals.on_database_delete.connect(self._on_database_delete)
        signals.on_database_reset.connect(self._on_database_reset)
        signals.on_database_write.connect(self._on_database_write)

        signals.project_changed.connect(self._on_project_changed)
        signals.project_created.connect(self._on_project_created)

        signals.on_activity_parameter_recalculate.connect(self._on_parameter_recalculate)
        signals.on_database_parameter_recalculate.connect(self._on_parameter_recalculate)
        signals.on_project_parameter_recalculate.connect(self._on_parameter_recalculate)
        signals.on_activity_parameter_recalculate_exchanges.connect(self._on_parameterized_exchange_recalculate)

        databases._save_signal.connect(self._on_database_metadata_change)
        setattr(methods, "_save_signal", blinker_signal("ab.patched_methods"))
        methods._save_signal.connect(self._on_methods_metadata_change)

        Method._write_signal.connect(self._on_method_write)
        Method._deregister_signal.connect(self._on_method_deregister)

    def _on_signaleddataset_on_save(self, sender, old, new):
        from bw2data.backends import ActivityDataset, ExchangeDataset
        from bw2data.parameters import ProjectParameter, DatabaseParameter, ActivityParameter

        if isinstance(new, ActivityDataset):
            self.node.changed.emit(new, old)
        elif isinstance(new, ExchangeDataset):
            self.edge.changed.emit(new, old)
        elif isinstance(new, (ProjectParameter, DatabaseParameter, ActivityParameter)):
            self.parameter.changed.emit(new, old)
        else:
            print(f"Unknown dataset type changed: {type(new)}")

    def _on_signaleddataset_on_delete(self, sender, old):
        from bw2data.backends import ActivityDataset, ExchangeDataset
        from bw2data.parameters import ProjectParameter, DatabaseParameter, ActivityParameter

        if isinstance(old, ActivityDataset):
            self.node.deleted.emit(old)
        elif isinstance(old, ExchangeDataset):
            self.edge.deleted.emit(old)
        elif isinstance(old, (ProjectParameter, DatabaseParameter, ActivityParameter)):
            self.parameter.deleted.emit(old)
        else:
            print(f"Unknown dataset type deleted: {type(old)}")

    def _on_activity_database_change(self, sender, old, new):
        self.node.database_change.emit(old, new)

    def _on_activity_code_change(self, sender, old, new):
        self.node.code_change.emit(old, new)

    def _on_database_delete(self, sender, name):
        self.database.deleted.emit(name)

    def _on_database_reset(self, sender, name):
        from bw2data import Database
        self.database.reset.emit(Database(name))

    def _on_database_write(self, sender, name):
        from bw2data import Database
        self.database.written.emit(Database(name))

    def _on_project_changed(self, ds):
        self.project.changed.emit()

    def _on_project_created(self, ds):
        self.project.created.emit()

    def _on_database_metadata_change(self, sender, old, new):
        self.meta.databases_changed.emit(old, new)

    def _on_methods_metadata_change(self, sender, old, new):
        self.meta.methods_changed.emit(old, new)

    def _on_method_write(self, sender):
        self.method.changed.emit(sender)

    def _on_method_deregister(self, sender):
        self.method.deleted.emit(sender)

    def _on_parameter_recalculate(self, sender, *args, **kwargs):
        self.parameter.recalculated.emit()

    def _on_parameterized_exchange_recalculate(self, sender, *args, **kwargs):
        self.edge.recalculated.emit()


def patch_methods_datastore():
    from bw2data import Method

    def write(self, data, process=True):
        original_write(self, data, process)
        self._write_signal.send(self)

    def deregister(self):
        original_deregister(self)
        self._deregister_signal.send(self)

    original_write = Method.write
    original_deregister = Method.deregister

    setattr(Method, "write", write)
    setattr(Method, "deregister", deregister)

    setattr(Method, "_write_signal", blinker_signal("ab.patched_method_write"))
    setattr(Method, "_deregister_signal", blinker_signal("ab.patched_method_deregister"))


patch_methods_datastore()

signals = ABSignals()
