import brightway2 as bw
from PySide2 import QtCore, QtWidgets
from activity_browser.signals import signals
from activity_browser.ui.widgets.dialog import EcoinventVersionDialog
from activity_browser.ui.widgets.dialog import ProjectDeletionDialog
import pytest

from activity_browser import Application

def test_biosphere_install(qtbot, qapp, monkeypatch):
    monkeypatch.setattr(
        QtWidgets.QInputDialog, 'getText',
        staticmethod(lambda *args, **kwargs: ('pytest_project', True))
    )
    monkeypatch.setattr(
        ProjectDeletionDialog, "exec_",
        staticmethod(lambda *args: ProjectDeletionDialog.Accepted)
    )
    monkeypatch.setattr(
        ProjectDeletionDialog, "deletion_warning_checked",
        staticmethod(lambda *args: True)
    )
    monkeypatch.setattr(
        QtWidgets.QMessageBox, "information",
        staticmethod(lambda *args: True)
    )
    app = Application()
    app.show()
    
    assert bw.projects.current == 'default'
    qtbot.waitExposed(app.main_window)

    if 'pytest_project' in bw.projects:
        bw.projects.delete_project('pytest_project', delete_dir=True)
        signals.projects_changed.emit()

    # fake the project name text input when called

    project_tab = app.main_window.left_panel.tabs['Project']
    qtbot.mouseClick(
        project_tab.projects_widget.new_project_button,
        QtCore.Qt.LeftButton
    )
    assert bw.projects.current == 'pytest_project'

    # The biosphere3 import finishes with a 'change_project' signal.
    with qtbot.waitSignal(signals.change_project, timeout=10*60*1000):  # allow 10 mins for biosphere install

        # fake the accepting of the dialog when started
        monkeypatch.setattr(EcoinventVersionDialog, 'exec_', lambda self: EcoinventVersionDialog.Accepted)

        # click the 'add default data' button
        qtbot.mouseClick(
            project_tab.databases_widget.add_default_data_button,
            QtCore.Qt.LeftButton
        )

    # The biosphere3 update finishes with a 'database_changed' signal.
    with qtbot.waitSignal(signals.database_changed, timeout=2 * 60 * 1000):  # allow 2 mins for biosphere update
        pass

    # biosphere was installed
    assert 'biosphere3' in bw.databases

    assert bw.projects.current == 'pytest_project'
    # delete project
    project_tab = app.main_window.left_panel.tabs['Project']
    qtbot.mouseClick(
        project_tab.projects_widget.delete_project_button,
        QtCore.Qt.LeftButton
    )

    assert bw.projects.current == 'default'

    app.close()
    #qapp.exit()