from typing import Union, Callable

from PySide2 import QtWidgets, QtCore

from activity_browser import application, database_controller
from activity_browser.actions.base import ABAction
from activity_browser.ui.icons import qicons
from activity_browser.ui.widgets import DatabaseLinkingDialog, DatabaseLinkingResultsDialog
from activity_browser.bwutils.strategies import relink_exchanges_existing_db


class DatabaseRelink(ABAction):
    """
    ABAction to relink the dependencies of a database.
    """
    icon = qicons.edit
    title = "Relink the database"
    tool_tip = "Relink the dependencies of this database"
    db_name: str

    def __init__(self, database_name: Union[str, Callable], parent: QtCore.QObject):
        super().__init__(parent, db_name=database_name)

    def onTrigger(self, toggled):
        db_name = self.db_name
        # get brightway database object
        db = database_controller.get(db_name)

        # find the dependencies of the database and construct a list of suitable candidates
        depends = db.find_dependents()
        options = [(depend, list(database_controller)) for depend in depends]

        # construct a dialog in which the user chan choose which depending database to connect to which candidate
        dialog = DatabaseLinkingDialog.relink_sqlite(db_name, options, application.main_window)

        # return if the user cancels
        if dialog.exec_() != DatabaseLinkingDialog.Accepted: return

        # else, start the relinking
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        relinking_results = dict()

        # relink using relink_exchanges_existing_db strategy
        for old, new in dialog.relink.items():
            other = database_controller.get(new)
            failed, succeeded, examples = relink_exchanges_existing_db(db, old, other)
            relinking_results[f"{old} --> {other.name}"] = (failed, succeeded)

        QtWidgets.QApplication.restoreOverrideCursor()

        # if any failed, present user with results dialog
        if failed > 0:
            relinking_dialog = DatabaseLinkingResultsDialog.present_relinking_results(application.main_window,
                                                                                      relinking_results, examples)
            relinking_dialog.exec_()
            relinking_dialog.open_activity()