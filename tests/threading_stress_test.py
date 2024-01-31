import brightway2 as bw
from PySide2 import QtCore, QtWidgets
from activity_browser.signals import signals
from activity_browser.ui.widgets.dialog import EcoinventVersionDialog
from activity_browser.ui.widgets.dialog import ProjectDeletionDialog
from activity_browser.ui.widgets import DatabaseLinkingDialog
from activity_browser.ui.wizards.db_import_wizard import DatabaseImportWizard, ImportPage
import pytest
import os

from activity_browser import Application

def test_biosphere_install(qtbot, qapp, monkeypatch):
    # setting up different monkeypatches

    # monkeypatch for the create project popup
    monkeypatch.setattr(
        QtWidgets.QInputDialog, 'getText',
        staticmethod(lambda *args, **kwargs: ('pytest_project', True))
    )

    monkeypatch.setattr(
        DatabaseLinkingDialog, "exec_",
        staticmethod(lambda *args: DatabaseLinkingDialog.Accepted)
    )

    # monkeypatches for the deletion "are you sure" dialogue
    monkeypatch.setattr(
        ProjectDeletionDialog, "deletion_warning_checked",
        staticmethod(lambda *args: True)
    )
    monkeypatch.setattr(
        ProjectDeletionDialog, "exec_",
        staticmethod(lambda *args: ProjectDeletionDialog.Accepted)
    )

    # monkeypatch for the deletion confirmation dialogue
    monkeypatch.setattr(
        QtWidgets.QMessageBox, "information",
        staticmethod(lambda *args: True)
    )

    app = Application()
    app.show()
    qtbot.waitExposed(app.main_window)

    # make sure pytest_project isn't actually there
    if 'pytest_project' in bw.projects:
        bw.projects.delete_project('pytest_project', delete_dir=True)
        signals.projects_changed.emit()

    # create new project called pytest_project
    project_tab = app.main_window.left_panel.tabs['Project']
    qtbot.mouseClick(
        project_tab.projects_widget.new_project_button,
        QtCore.Qt.LeftButton
    )
    assert bw.projects.current == 'pytest_project'

    # Import biosphere3
    with qtbot.waitSignal(signals.change_project, timeout=10*60*1000):  # allow 10 mins for biosphere install

        # fake the accepting of the dialog when started
        monkeypatch.setattr(EcoinventVersionDialog, 'exec_', lambda self: EcoinventVersionDialog.Accepted)

        # click the 'add default data' button
        qtbot.mouseClick(
            project_tab.databases_widget.add_default_data_button,
            QtCore.Qt.LeftButton
        )

    # Patch biosphere3
    with qtbot.waitSignal(signals.database_changed, timeout=2 * 60 * 1000):  # allow 2 mins for biosphere update
        pass

    # biosphere was installed
    assert 'biosphere3' in bw.databases

    # # Import background Database
    # background_wizard = DatabaseImportWizard()
    # with qtbot.waitSignal(signals.databases_changed, timeout=10*60*1000):  # allow 10 mins for biosphere install
    #     background_wizard.setStartId(12)
    #     background_wizard.import_type = "local"
    #     background_wizard.setField("db_name","ei39-remind-SSP2")
    #     background_wizard.setField("archive_path", os.getcwd() + "\\tests\\ei39-remind-SSP2.bw2package")
    #     background_wizard.show()
    # background_wizard.done(0)
    # assert 'ei39-remind-SSP2' in bw.databases

    # # Import foreground Database
    # foreground_wizard = DatabaseImportWizard()
    # with qtbot.waitSignal(signals.databases_changed, timeout=10*60*1000):  # allow 10 mins for biosphere install
    #     foreground_wizard.setStartId(12)
    #     foreground_wizard.import_type = "local"
    #     foreground_wizard.setField("db_name","EV case")
    #     foreground_wizard.setField("archive_path", os.getcwd() + "\\tests\\EV case.xlsx")
    #     foreground_wizard.show()
    # foreground_wizard.done(0)
    # assert 'EV case' in bw.databases


    # delete the pytest project
    project_tab = app.main_window.left_panel.tabs['Project']
    qtbot.mouseClick(
        project_tab.projects_widget.delete_project_button,
        QtCore.Qt.LeftButton
    )
