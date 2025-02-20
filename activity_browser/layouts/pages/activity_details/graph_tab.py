import json
import os
from logging import getLogger

import numpy as np

from qtpy import QtWebChannel, QtWebEngineWidgets, QtWidgets
from qtpy.QtCore import QObject, Qt, QUrl, Signal, SignalInstance, Slot

import bw2data as bd
import bw_functional as bf

from activity_browser import static
from activity_browser.bwutils import refresh_node

log = getLogger(__name__)

class GraphTab(QtWidgets.QWidget):

    def __init__(self, activity, parent=None):
        super().__init__(parent)
        self.activity = refresh_node(activity)
        self.expanded_nodes = {self.activity.id}

        self.button = QtWidgets.QPushButton("CLICK ME")
        self.button.clicked.connect(self.sync)

        self.bridge = Bridge(self)
        self.url = QUrl.fromLocalFile(os.path.join(static.__path__[0], "activity_graph.html"))

        self.channel = QtWebChannel.QWebChannel(self)
        self.channel.registerObject("bridge", self.bridge)
        self.channel.registerObject("backend", self)

        self.page = Page()
        self.page.setWebChannel(self.channel)

        self.view = QtWebEngineWidgets.QWebEngineView(self)
        self.view.setContextMenuPolicy(Qt.PreventContextMenu)
        self.view.setPage(self.page)
        self.view.setUrl(self.url)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.view)
        # layout.addWidget(self.button)
        self.setLayout(layout)

        self.bridge.ready.connect(self.sync)

    def sync(self):
        self.activity = refresh_node(self.activity)
        json = self.build_json()
        self.bridge.update_graph.emit(json)

    def build_json(self):
        nodes = []
        edges = []

        collapsed_functions = set()
        for node_id in self.expanded_nodes:
            node = bd.get_node(id=node_id)
            excs = list(node.exchanges())
            function_nodes = [exc.input for exc in excs if exc["type"] == "production"]
            functions = []

            for fn_node in function_nodes:
                functions.append({
                    "id": f"bw{fn_node.id}",
                    "name": fn_node._document.product if fn_node._document.product else fn_node["name"]
                })
                excs.extend(fn_node.upstream())

            nodes.append({
                "id": f"bw{node.id}",
                "name": node["name"],
                "functions": functions,
                "type": "expanded_node"
            })

            for exc in excs:
                if exc["type"] in ["production", "biosphere"]:
                    continue
                processor = get_processor_from_exchange(exc)

                source_id = processor.id
                target_id = exc.output.id

                if source_id not in self.expanded_nodes:
                    source_id = exc.input.id
                    collapsed_functions.add(source_id)

                if target_id not in self.expanded_nodes:
                    collapsed_functions.add(target_id)

                edges.append({
                    "source_id": f"bw{source_id}",
                    "target_id": f"bw{exc.output.id}",
                    "function_id": f"bw{exc.input.id}",
                })

        for node_id in collapsed_functions:
            fn_node = bd.get_node(id=node_id)
            nodes.append({
                "id": f"bw{node_id}",
                "name": fn_node._document.product if fn_node._document.product else fn_node["name"],
                "functions": [],
                "type": "collapsed_function"
            })

        full = {
            "nodes": nodes,
            "edges": edges,
        }

        return json.dumps(full)

    @Slot(str)
    def expand_node(self, node_id: str):
        node_id = int(node_id)  # JS shenanigans can't deal with 64 bit strings
        node = bd.get_node(id=node_id)
        if isinstance(node, bf.Function):
            node = bd.get_node(key=node["processor"])
        self.expanded_nodes.add(node.id)
        self.sync()

    @Slot(str)
    def collapse_node(self, node_id: str):
        node_id = int(node_id)  # JS shenanigans can't deal with 64 bit strings
        if self.activity.id == node_id:
            return
        self.expanded_nodes.remove(int(node_id))
        self.sync()


def get_processor_from_exchange(exchange):
    source = exchange.input
    processors = list(source.upstream(kinds=["production"]))
    if len(processors) > 1:
        log.warning("Multiple processors, only taking first one")
    processor = processors[0]
    return processor.output


class Bridge(QObject):
    update_graph: SignalInstance = Signal(str)
    ready: SignalInstance = Signal()

    @Slot()
    def is_ready(self):
        self.ready.emit()


class Page(QtWebEngineWidgets.QWebEnginePage):
    def javaScriptConsoleMessage(self, level: QtWebEngineWidgets.QWebEnginePage.JavaScriptConsoleMessageLevel, message: str, line: str, _: str):
        if level == QtWebEngineWidgets.QWebEnginePage.InfoMessageLevel:
            log.info(f"JS Info (Line {line}): {message}")
        elif level == QtWebEngineWidgets.QWebEnginePage.WarningMessageLevel:
            log.warning(f"JS Warning (Line {line}): {message}")
        elif level == QtWebEngineWidgets.QWebEnginePage.ErrorMessageLevel:
            log.error(f"JS Error (Line {line}): {message}")
        else:
            log.debug(f"JS Log (Line {line}): {message}")
