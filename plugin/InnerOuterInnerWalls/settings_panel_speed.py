import json
import os
import time
from typing import Any, Dict, Optional

from PyQt6.QtCore import QMetaObject, QTimer

from UM.Logger import Logger
from cura.CuraApplication import CuraApplication


class SettingsPanelSpeed:
    """Part of the Inner/Outer/Inner plugin. The print settings list builds a widget for every visible setting of every expanded category, at roughly 15 ms each. With the
    "All" preset and every category expanded that is over 700 widgets, which freezes the interface for several seconds. This add-on
    does what "Collapse All Categories" does, automatically: when a preset with many settings is chosen (and at startup, if the saved
    state has everything expanded) the categories are collapsed first, so the list only holds the category headers and each
    category is built when it is opened. Nothing in Cura itself is modified.

    settings_panel.json (optional, next to this file): "mode" is "collapse" (default) or "measure" (only log the build times); "min_settings" is the size
    of a preset that triggers the collapse; "startup_expanded" is how many saved expanded entries count as "everything expanded"."""

    def __init__(self) -> None:
        self._app = CuraApplication.getInstance()
        self._config = self._read_config()
        self._list = None  # type: Any
        self._hooked = False
        self._last_count = -1
        self._last_ready = -1
        self._burst_start = None  # type: Optional[float]
        self._last_change = 0.0
        self._failed = False
        self._errors = 0
        self._last_tick = time.monotonic()
        self._stall_total = 0.0
        self._stall_max = 0.0
        Logger.log("i", "Inner/Outer/Inner plugin, settings panel: mode %s", self._config["mode"])

        self._collapse_saved_state_at_startup()

        self._timer = QTimer()
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    @staticmethod
    def _read_config() -> Dict[str, Any]:
        config = {"mode": "collapse", "min_settings": 300, "startup_expanded": 150}
        try:
            with open(os.path.join(os.path.dirname(__file__), "settings_panel.json"), encoding = "utf-8") as f:
                config.update(json.load(f))
        except Exception:
            Logger.log("w", "Inner/Outer/Inner plugin, settings panel: could not read settings_panel.json, using defaults")
        return config

    def _collapse_saved_state_at_startup(self) -> None:
        if self._config["mode"] != "collapse":
            return
        try:
            saved = [entry for entry in (self._app.getPreferences().getValue("cura/categories_expanded") or "").split(";") if entry]  # Nothing saved yet: no value.
            if len(saved) >= int(self._config["startup_expanded"]):
                self._app.setExpandedCategories([])
                Logger.log("i", "Inner/Outer/Inner plugin, settings panel: the saved state had %s expanded entries, collapsed all categories at startup", len(saved))
        except Exception:
            Logger.logException("e", "Inner/Outer/Inner plugin, settings panel: could not check the saved expanded categories")

    def _find_list(self) -> Any:
        engine = getattr(self._app, "_qml_engine", None)
        if engine is None or not engine.rootObjects():
            return None
        stack = [engine.rootObjects()[0].contentItem()]
        while stack:
            item = stack.pop()
            if item.metaObject().className().startswith("QQuickListView"):
                model = item.property("model")
                if model is not None and "SettingDefinitionsModel" in model.metaObject().className():
                    return item
                continue  # Do not walk into other lists: their delegates can be numerous.
            stack.extend(item.childItems())
        return None

    def _hook_presets(self) -> None:
        presets = self._app.getSettingVisibilityPresetsModel()
        if presets is None:
            return
        presets.activePresetChanged.connect(self._on_preset_changed)
        self._hooked = True
        Logger.log("i", "Inner/Outer/Inner plugin, settings panel: watching the visible settings preset")

    def _on_preset_changed(self) -> None:
        if self._config["mode"] != "collapse":
            return
        try:
            presets = self._app.getSettingVisibilityPresetsModel()
            preset = presets.getVisibilityPresetById(presets.activePreset)
            size = len(preset.settings) if preset is not None else 0
            if size < int(self._config["min_settings"]):
                return
            collapsed_in_list = False
            settings_list = self._list if self._list is not None else self._find_list()
            if settings_list is not None:
                model = settings_list.property("model")
                try:
                    model.collapseAllCategories()
                except Exception:
                    collapsed_in_list = QMetaObject.invokeMethod(model, "collapseAllCategories")
                else:
                    collapsed_in_list = True
            self._app.setExpandedCategories([])  # Also covers the case where the list does not exist yet.
            Logger.log("i", "Inner/Outer/Inner plugin, settings panel: preset %s has %s settings, collapsed all categories (list updated: %s)", presets.activePreset, size, collapsed_in_list)
        except Exception:
            Logger.logException("e", "Inner/Outer/Inner plugin, settings panel: could not collapse the categories")

    def _tick(self) -> None:
        if self._failed:
            return
        now = time.monotonic()
        stall = now - self._last_tick - 0.1  # The timer is meant to fire every 0.1 s; anything beyond that is the interface being busy.
        self._last_tick = now
        if stall > 0.3:
            self._stall_total += stall
            self._stall_max = max(self._stall_max, stall)
            Logger.log("d", "Inner/Outer/Inner plugin, settings panel: interface was unresponsive for %.2f s", stall)
        try:
            if not self._hooked:
                self._hook_presets()
            self._poll()
            self._errors = 0
        except Exception:
            # Most likely the settings list was destroyed (for example when its tab was closed): forget it and look for the next one.
            self._list = None
            self._burst_start = None
            self._last_count = -1
            self._last_ready = -1
            self._errors += 1
            if self._errors >= 20:
                self._failed = True
                Logger.logException("e", "Inner/Outer/Inner plugin, settings panel: stopped after repeated errors")

    def _poll(self) -> None:
        if self._list is None:
            if int(time.monotonic() * 10) % 5 != 0:  # Searching the item tree is cheap, but only do it every half second.
                return
            self._list = self._find_list()
            if self._list is None:
                return
            Logger.log("i", "Inner/Outer/Inner plugin, settings panel: found the settings list")
            if self._config["mode"] == "collapse" and int(self._list.property("count")) >= int(self._config["min_settings"]):
                # Cura can re-read its saved state after add-ons start, so a startup check alone is not enough.
                self._list.property("model").collapseAllCategories()
                Logger.log("i", "Inner/Outer/Inner plugin, settings panel: the list had %s rows, collapsed all categories", self._list.property("count"))

        children = self._list.property("contentItem").childItems()
        count = int(self._list.property("count"))
        ready = 0
        for child in children:
            if child.property("item") is not None:  # The Loader has finished creating its content (the Status enum cannot be read from Python).
                ready += 1
        now = time.monotonic()
        if count != self._last_count or ready != self._last_ready:
            if self._burst_start is None:
                self._burst_start = now
                self._stall_total = 0.0
                self._stall_max = 0.0
                Logger.log("d", "Inner/Outer/Inner plugin, settings panel: building started (rows %s, widgets %s, ready %s)", count, len(children), ready)
            self._last_change = now
            self._last_count = count
            self._last_ready = ready
        elif self._burst_start is not None and now - self._last_change > 1.5:
            Logger.log("d", "Inner/Outer/Inner plugin, settings panel: building finished in %.2f s (wall clock), of which the interface was frozen %.2f s (longest freeze %.2f s) (rows %s, widgets %s, ready %s)",
                       self._last_change - self._burst_start, self._stall_total, self._stall_max, count, len(children), ready)
            self._burst_start = None
