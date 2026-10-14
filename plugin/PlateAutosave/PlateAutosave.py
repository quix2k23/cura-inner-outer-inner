import io
import os
import zipfile

from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlComponent

from UM.Extension import Extension
from UM.Logger import Logger
from UM.Mesh.MeshWriter import MeshWriter
from UM.Resources import Resources

from cura.CuraApplication import CuraApplication

PREF_ENABLED = "plate_autosave/enabled"
PREF_INTERVAL = "plate_autosave/interval_minutes"
DEFAULT_INTERVAL_MIN = 5
MAX_INTERVAL_MIN = 1440
RESTORE_DELAY_MS = 3000
DIALOG_POLL_MS = 500

# Cura offers no hook for plugins to add Preferences controls, so these are inserted into the live
# "Opening and saving files" section, right after the item whose text is ANCHOR_TEXT (English UI).
ANCHOR_TEXT = "Show summary dialog when saving project"
MARKER_NAME = "plateAutosaveInjected"
CONTROLS_QML = b"""
import QtQuick 2.10
import QtQuick.Controls 2.15
import UM 1.5 as UM
import Cura 1.1 as Cura

Column
{
    objectName: "plateAutosaveInjected"

    function isTrue(v) { return v === true || String(v).toLowerCase() === "true" }

    UM.TooltipArea
    {
        width: childrenRect.width
        height: childrenRect.height
        text: "Save the build plate layout periodically and when quitting, and restore it when Cura starts"

        UM.CheckBox
        {
            id: enabledCheckbox
            text: "Autosave build plate layout"
            checked: isTrue(UM.Preferences.getValue("plate_autosave/enabled"))
            onClicked: UM.Preferences.setValue("plate_autosave/enabled", checked)
        }
    }

    UM.TooltipArea
    {
        width: childrenRect.width
        height: childrenRect.height
        text: "How often the build plate layout is autosaved (1 to 1440 minutes)"

        Row
        {
            spacing: UM.Theme.getSize("default_margin").width
            enabled: enabledCheckbox.checked

            UM.Label
            {
                text: "Autosave interval (minutes)"
                height: intervalField.height
                verticalAlignment: Text.AlignVCenter
            }

            Cura.TextField
            {
                id: intervalField
                width: 70 * screenScaleFactor
                text: String(UM.Preferences.getValue("plate_autosave/interval_minutes"))
                validator: IntValidator { bottom: 1; top: 1440 }
                onEditingFinished:
                {
                    var minutes = parseInt(text)
                    if (!isNaN(minutes))
                    {
                        UM.Preferences.setValue("plate_autosave/interval_minutes", Math.max(1, Math.min(1440, minutes)))
                    }
                }
            }
        }
    }
}
"""


class PlateAutosave(Extension):
    """Periodically stores the plate as a plain (non-project) 3MF and reloads it on startup.

    A non-project 3MF is not asked about on open and the 3MF reader keeps the stored
    positions (no re-arranging), so the layout comes back exactly as it was.
    """

    def __init__(self) -> None:
        super().__init__()
        self._app = CuraApplication.getInstance()
        # Kept outside the versioned config folder: the version-upgrade scan there tries to parse every file
        # it finds and logs two warnings per save file on each start.
        legacy_path = os.path.join(Resources.getDataStoragePath(), "plate_autosave.3mf")
        save_dir = os.path.join(os.path.dirname(Resources.getDataStoragePath()), "plate_autosave")
        os.makedirs(save_dir, exist_ok = True)
        self._path = os.path.join(save_dir, "plate_autosave.3mf")
        self._migrateLegacy(legacy_path)
        self._restored = False

        preferences = self._app.getPreferences()
        preferences.addPreference(PREF_ENABLED, True)
        preferences.addPreference(PREF_INTERVAL, DEFAULT_INTERVAL_MIN)
        preferences.preferenceChanged.connect(self._onPreferenceChanged)

        self._timer = QTimer()
        self._timer.setInterval(self._intervalMs())
        self._timer.timeout.connect(self._save)

        # The Preferences dialog is rebuilt on every open and on every tab switch, so keep checking for it.
        self._dialog_timer = QTimer()
        self._dialog_timer.setInterval(DIALOG_POLL_MS)
        self._dialog_timer.timeout.connect(self._injectControls)
        self._dialog_timer.start()
        self._injection_logged = False

        self._app.initializationFinished.connect(self._onStarted)
        # aboutToQuit never fires (Cura ends with os._exit) and closeApplication drops the printer first,
        # so use Cura's own pre-exit callback chain, which runs while everything is still intact.
        self._app.getOnExitCallbackManager().addCallback(self._saveOnQuit)

    def _migrateLegacy(self, legacy_path: str) -> None:
        """Move saves written by older versions of this plugin; they are newer than anything in the new folder."""
        for suffix in ("", ".prev"):
            try:
                if os.path.exists(legacy_path + suffix):
                    os.replace(legacy_path + suffix, self._path + suffix)
            except OSError:
                Logger.logException("w", "PlateAutosave: could not move old save file")

    def _enabled(self) -> bool:
        return str(self._app.getPreferences().getValue(PREF_ENABLED)).lower() == "true"

    def _intervalMs(self) -> int:
        try:
            minutes = int(float(self._app.getPreferences().getValue(PREF_INTERVAL)))
        except (TypeError, ValueError):
            minutes = DEFAULT_INTERVAL_MIN
        return max(1, min(MAX_INTERVAL_MIN, minutes)) * 60 * 1000

    def _onPreferenceChanged(self, name: str) -> None:
        if name not in (PREF_ENABLED, PREF_INTERVAL):
            return
        self._timer.setInterval(self._intervalMs())
        if self._restored:  # before the startup restore has run the timer must stay stopped
            if self._enabled():
                self._timer.start()
            else:
                self._timer.stop()
        Logger.info("PlateAutosave: setting changed: enabled=%s, interval=%d min", self._enabled(), self._timer.interval() // 60000)

    @staticmethod
    def _findByText(item, text):
        if item.property("text") == text:
            return item
        for child in item.childItems():
            found = PlateAutosave._findByText(child, text)
            if found is not None:
                return found
        return None

    @staticmethod
    def _hasMarker(item) -> bool:
        if item.objectName() == MARKER_NAME:
            return True
        return any(PlateAutosave._hasMarker(child) for child in item.childItems())

    def _injectControls(self) -> None:
        try:
            for window in QGuiApplication.topLevelWindows():
                if window.title() != "Preferences" or not window.isVisible() or not hasattr(window, "contentItem"):
                    continue
                root = window.contentItem()
                anchor = self._findByText(root, ANCHOR_TEXT)
                if anchor is None or self._hasMarker(anchor.parentItem().parentItem()):
                    continue  # page not loaded yet (or another tab is showing), or already injected
                tooltip_area = anchor.parentItem()
                column = tooltip_area.parentItem()
                engine = self._app._qml_engine
                component = QQmlComponent(engine)
                component.setData(CONTROLS_QML, QUrl())
                controls = component.create(engine.rootContext())
                if controls is None:
                    Logger.warning("PlateAutosave: could not create controls: %s", component.errorString())
                    return
                controls.setParent(column)
                controls.setParentItem(column)
                controls.stackAfter(tooltip_area)
                if not self._injection_logged:
                    Logger.info("PlateAutosave: added preference controls (y=%s, anchor y=%s)", controls.y(), tooltip_area.y())
                    self._injection_logged = True
        except Exception:
            Logger.logException("e", "PlateAutosave: could not add preference controls")
            self._dialog_timer.stop()

    def _onStarted(self) -> None:
        Logger.info("PlateAutosave: startup finished, restoring in %d ms", RESTORE_DELAY_MS)
        QTimer.singleShot(RESTORE_DELAY_MS, self._restore)

    def _plateNodes(self):
        root = self._app.getController().getScene().getRoot()
        plate = self._app.getMultiBuildPlateModel().activeBuildPlate
        return [n for n in root.getChildren()
                if (n.callDecoration("isSliceable") or n.callDecoration("isGroup"))
                and n.callDecoration("getBuildPlateNumber") == plate]

    def _loadableSave(self):
        """The newest save that is a valid 3MF: the main file, else the .prev left by an interrupted swap."""
        for path in (self._path, self._path + ".prev"):
            try:
                with open(path, "rb") as f:
                    if self._isValid(f.read(), 1):
                        return path
                Logger.warning("PlateAutosave: %s is not a valid save, trying the next", path)
            except OSError:
                pass
        return None

    def _restore(self) -> None:
        try:
            path = self._loadableSave()
            Logger.info("PlateAutosave: restore check, usable save: %s", path)
            # Files given on the command line (e.g. an STL double-clicked in a file manager) load in a background job,
            # so the plate can still look empty here; restoring would put the old plate in their place.
            launched_with_files = bool(getattr(self._app, "_files_to_open", None) or getattr(self._app, "_open_file_queue", None))
            if launched_with_files:
                Logger.info("PlateAutosave: Cura was opened with files, not restoring")
            elif path and self._enabled() and not self._plateNodes():
                Logger.info("PlateAutosave: restoring %s", path)
                self._app.readLocalFile(QUrl.fromLocalFile(path), add_to_recent_files = False)
        except Exception:
            Logger.logException("e", "PlateAutosave: restore failed")
        finally:
            # Only start saving after the restore attempt, so an empty startup plate can't wipe the save.
            self._restored = True
            if self._enabled():
                self._timer.start()

    def _saveOnQuit(self) -> None:
        try:
            if self._enabled():
                self._save(final = True)
        finally:
            # Always let the exit proceed, whatever happened above.
            self._app.getOnExitCallbackManager().onCurrentCallbackFinished(True)

    @staticmethod
    def _isValid(data: bytes, expected_nodes: int) -> bool:
        """Sanity check of the written 3MF, so a bad write can never replace a good save."""
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                if z.testzip() is not None:
                    return False
                return z.read("3D/3dmodel.model").count(b"<item ") >= expected_nodes
        except Exception:
            return False

    def _save(self, final: bool = False) -> None:
        if not self._restored or self._app.getGlobalContainerStack() is None:
            return
        writer = None
        orig_snapshot = None
        try:
            nodes = self._plateNodes()
            Logger.info("PlateAutosave: %s, %d node(s) on plate", "quit save" if final else "timer fired", len(nodes))
            if not nodes:
                for path in (self._path, self._path + ".prev"):
                    if os.path.exists(path):
                        os.remove(path)
                return
            writer = self._app.getMeshFileHandler().getWriter("3MFWriter")
            if writer is None:
                return
            if final:
                # No thumbnail on quit: rendering during shutdown can hang, and the writer's snapshot
                # helper leaves its lock held when the renderer is gone.
                orig_snapshot = writer._createSnapshot
                writer._createSnapshot = lambda: None
            stream = io.BytesIO()
            if not writer.write(stream, nodes, MeshWriter.OutputMode.BinaryMode):
                Logger.warning("PlateAutosave: 3MF writer failed, keeping previous save")
                return
            data = stream.getvalue()
            if not self._isValid(data, len(nodes)):
                Logger.warning("PlateAutosave: written 3MF failed validation, keeping previous save")
                return
            tmp = self._path + ".tmp"
            with open(tmp, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            if os.path.exists(self._path):
                os.replace(self._path, self._path + ".prev")
            os.replace(tmp, self._path)
            Logger.info("PlateAutosave: saved %d node(s) to %s", len(nodes), self._path)
        except Exception:
            Logger.logException("e", "PlateAutosave: save failed, keeping previous save")
        finally:
            if orig_snapshot is not None:
                writer._createSnapshot = orig_snapshot
