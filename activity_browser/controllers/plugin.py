# -*- coding: utf-8 -*-
import importlib.util
from pkgutil import iter_modules

from PySide2.QtCore import QObject

from activity_browser import (ab_settings, application, log, project_settings,
                              signals)
from activity_browser.mod import bw2data as bd


class PluginController(QObject):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.connect_signals()
        # Shortcut to ab_settings plugins list
        self.plugins = ab_settings.plugins
        self.load_plugins()

    def connect_signals(self):
        bd.projects.current_changed.connect(self.reload_plugins)
        signals.plugin_selected.connect(self.add_plugin)

    def load_plugins(self):
        names = self.discover_plugins()
        for name in names:
            plugin = self.load_plugin(name)
            if plugin:
               self.plugins[name] = plugin

    def discover_plugins(self):
        plugins = []
        for module in iter_modules():
            if module.name.startswith("ab_plugin"):
                plugins.append(module.name)
        return plugins

    def load_plugin(self, name):
        try:
            log.info("Importing plugin {}".format(name))
            plugin_lib = importlib.import_module(name)
            importlib.reload(plugin_lib)
            return plugin_lib.Plugin()
        except Exception as e:
            log.error(f"Import of plugin module '{name}' failed. "
                      "If this keeps happening contact the plugin developers and let them know of this error:"
                      f"\n{e}")
            return None

    def add_plugin(self, name, select: bool = True):
        """add or reload tabs of the given plugin"""
        if select:
            plugin = self.plugins[name]
            try:
                plugin.load()
            except Exception as e:
                log.warning(f"Loading of plugin '{name}' failed. "
                            "If this keeps happening contact the plugin developers and let them know of this error:"
                            f"\n{e}")
                return

            # Add plugins tabs
            for tab in plugin.tabs:
                application.main_window.add_tab_to_panel(
                    tab, plugin.infos["name"], tab.panel
                )
            log.info(f"Loaded tab '{name}'")
            return

        log.info(f"Removing plugin '{name}'")
        # Apply plugin remove() function
        self.plugins[name].remove()
        # Close plugin tabs
        self.close_plugin_tabs(self.plugins[name])

    def close_plugin_tabs(self, plugin):
        for panel in (
            application.main_window.left_panel,
            application.main_window.right_panel,
        ):
            panel.close_tab_by_tab_name(plugin.infos["name"])

    def reload_plugins(self):
        """close all plugins tabs then import all plugins tabs"""
        plugins_list = [name for name in self.plugins.keys()]  # copy plugins list
        for name in plugins_list:
            self.close_plugin_tabs(self.plugins[name])
        for name in project_settings.get_plugins_list():
            if name in self.plugins:
                self.add_plugin(name)
            else:
                log.warning(f"Reloading of plugin '{name}' was skipped due to a previous error. "
                            "To reload this plugin, restart Activity Browser")

    def close(self):
        """close all plugins"""
        for plugin in self.plugins.values():
            plugin.close()


plugin_controller = PluginController(application)
