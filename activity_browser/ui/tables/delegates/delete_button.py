# -*- coding: utf-8 -*-
from PySide2 import QtCore, QtWidgets

from activity_browser import application


class DeleteButtonDelegate(QtWidgets.QStyledItemDelegate):
    """For showing a persistent delete button in tables"""

    delete_request = QtCore.Signal(QtCore.QModelIndex)

    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, 
                     parent: QtWidgets.QWidget, 
                     option: QtWidgets.QStyleOptionViewItem, 
                     index: QtCore.QModelIndex):
        button = QtWidgets.QPushButton()
        button.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        button.setFixedSize(20, 20)
        button.setAutoDefault(False)
        button.clicked.connect(lambda: self.delete_request.emit(index))
        style = application.style()
        icon = style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DockWidgetCloseButton)
        button.setIcon(icon)
        button.setStyleSheet("background-color: rgb(200, 150, 150); border-radius: 3")
        editor = QtWidgets.QWidget(parent)
        editor.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(button)
        editor.setLayout(layout)
        return editor
