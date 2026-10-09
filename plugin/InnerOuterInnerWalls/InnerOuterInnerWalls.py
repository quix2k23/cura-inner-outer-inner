import json
import os
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Set

from UM.Extension import Extension
from UM.Logger import Logger
from UM.Settings.ContainerRegistry import ContainerRegistry
from UM.Settings.DefinitionContainer import DefinitionContainer
from UM.Settings.SettingDefinition import SettingDefinition
from cura.CuraApplication import CuraApplication

FEATURES_FILE = "FEATURES"  # Written next to the patched engine; lists what that engine can do.

# New values for existing enum settings: (setting key, value id, label, engine feature that is needed or None).
NEW_OPTIONS = [
    ("inset_direction", "inner_outer_inner", "Inner/Outer/Inner", None),  # An engine without it prints inside out, which is harmless.
    ("infill_pattern", "bone", "Bone", "bone_infill"),  # An engine without it would print no infill at all.
]

# Where the new settings go: key of the existing setting or category they are added to, and the engine feature they need.
SETTING_PARENTS = {
    "infill_pattern": ("bone_infill", ["bone_seed", "bone_alignment", "bone_alignment_tilt", "bone_alignment_azimuth",
                                       "bone_irregularity", "bone_connectivity", "bone_cortical_width"]),
    "experimental": ("arc_fitting", ["arc_fitting_enable"]),
}
VISIBLE_KEYS = ["bone_seed", "bone_alignment", "bone_alignment_tilt", "bone_alignment_azimuth", "bone_irregularity",
                "bone_connectivity", "bone_cortical_width", "bone_cortical_lines",
                "arc_fitting_enable", "arc_fitting_tolerance", "arc_fitting_max_radius"]


class InnerOuterInnerWalls(Extension):
    def __init__(self) -> None:
        super().__init__()
        self._application = CuraApplication.getInstance()
        self._features = self._read_engine_features()
        Logger.log("i", "Inner/Outer/Inner plugin: engine features %s", sorted(self._features))

        self._setting_specs = OrderedDict()  # type: Dict[str, Any]
        try:
            with open(os.path.join(os.path.dirname(__file__), "settings.def.json"), encoding = "utf-8") as f:
                self._setting_specs = json.load(f, object_pairs_hook = OrderedDict)
        except Exception:
            Logger.logException("e", "Inner/Outer/Inner plugin: could not read the setting definitions")

        self._patch_definition_parsing()
        ContainerRegistry.getInstance().containerLoadComplete.connect(self._on_container_load_complete)
        self._application.globalContainerStackChanged.connect(self._patch_active_machine)
        self._application.initializationFinished.connect(self._on_initialization_finished)

    # --- Which features the engine has -------------------------------------------------------------------------

    def _read_engine_features(self) -> Set[str]:
        """The features listed in the FEATURES file next to the engine that Cura is configured to use."""
        location = None
        try:
            location = self._application.getPreferences().getValue("backend/location")
        except Exception:
            pass
        if not location:
            return set()
        try:
            with open(os.path.join(os.path.dirname(str(location)), FEATURES_FILE), encoding = "utf-8") as f:
                return {line.strip() for line in f if line.strip() and not line.startswith("#")}
        except OSError:
            return set()

    def _has(self, feature: Optional[str]) -> bool:
        return feature is None or feature in self._features

    # --- New values for existing settings ---------------------------------------------------------------------------

    def _add_options(self, definition: SettingDefinition) -> bool:
        for key, value, label, feature in NEW_OPTIONS:
            if definition.key == key and self._has(feature) and value not in definition.options:
                definition.extend_category(value, label)
                return True
        return False

    def _patch_definition_parsing(self) -> None:
        """Every definition container parses its own copy of a setting, so hook the parser itself."""
        if getattr(SettingDefinition, "_ioi_patched", False):
            return
        original = SettingDefinition._deserialize_dict
        plugin = self

        def patched(definition, serialized):
            original(definition, serialized)
            try:
                plugin._add_options(definition)
            except Exception as e:
                Logger.log("e", "Inner/Outer/Inner plugin: could not add an option: %s", e)

        SettingDefinition._deserialize_dict = patched
        SettingDefinition._ioi_patched = True

    # --- New settings ----------------------------------------------------------------------------------------------------

    def _add_setting(self, container: DefinitionContainer, parent: SettingDefinition, key: str) -> None:
        definition = SettingDefinition(key, container, parent, None)
        definition.deserialize(self._setting_specs[key])
        parent._children.append(definition)
        self._register(container, definition)

    def _register(self, container: DefinitionContainer, definition: SettingDefinition) -> None:
        """Make the container aware of a definition that was added after it was loaded, and of its children."""
        container._definition_cache[definition.key] = definition
        container._updateRelations(definition)
        for child in definition.children:
            self._register(container, child)

    def _extend_container(self, container: DefinitionContainer) -> List[str]:
        """Add the new options and settings to one printer definition. Safe to call more than once."""
        added = []  # type: List[str]
        if container.getMetaDataEntry("type") == "extruder":
            return added
        for key, value, label, feature in NEW_OPTIONS:
            for definition in container.findDefinitions(key = key):
                if self._add_options(definition):
                    added.append(value)
        for parent_key, (feature, keys) in SETTING_PARENTS.items():
            if not self._has(feature):
                continue
            parents = container.findDefinitions(key = parent_key)
            if not parents:
                continue
            for key in keys:
                if key in self._setting_specs and not container.findDefinitions(key = key):
                    self._add_setting(container, parents[0], key)
                    added.append(key)
        return added

    def _on_container_load_complete(self, container_id: str) -> None:
        try:
            if not ContainerRegistry.getInstance().isLoaded(container_id):
                return
            container = ContainerRegistry.getInstance().findContainers(id = container_id)[0]
            if isinstance(container, DefinitionContainer):
                self._extend_container(container)
        except Exception as e:
            Logger.log("e", "Inner/Outer/Inner plugin: could not extend definition %s: %s", container_id, e)

    def _patch_active_machine(self) -> None:
        """The printer that is active may have been loaded before this plugin; make sure it has everything."""
        try:
            stack = self._application.getGlobalContainerStack()
            if stack is None:
                return
            added = self._extend_container(stack.definition)
            container = stack.definition
            infill = container.findDefinitions(key = "infill_pattern")
            present = [key for key in VISIBLE_KEYS if container.findDefinitions(key = key)]
            Logger.log("i", "Inner/Outer/Inner plugin: printer '%s': added just now %s; infill patterns %s; wall orders %s; new settings present %s",
                       stack.getName(), added,
                       list(infill[0].options.keys())[-3:] if infill else None,
                       list(container.findDefinitions(key = "inset_direction")[0].options.keys()),
                       present)
        except Exception as e:
            Logger.log("e", "Inner/Outer/Inner plugin: could not check the active printer: %s", e)

    # --- Visibility ------------------------------------------------------------------------------------------------------

    def _on_initialization_finished(self) -> None:
        self._application.getPreferences().preferenceChanged.connect(self._fix_visibility)
        self._fix_visibility()

    def _fix_visibility(self, preference: str = "general/visible_settings") -> None:
        """Cura only shows settings that are in its visibility list, so add the new ones to it."""
        if preference != "general/visible_settings":
            return
        preferences = self._application.getPreferences()
        visible = preferences.getValue(preference)
        if not visible:
            return  # An empty list is replaced by a preset the first time the user changes the visibility.
        keys = set(visible.split(";"))
        wanted = [key for key in VISIBLE_KEYS if key in self._setting_specs or key in ("bone_cortical_lines", "arc_fitting_tolerance", "arc_fitting_max_radius")]
        missing = [key for key in wanted if key not in keys]
        if missing:
            preferences.setValue(preference, visible + ";" + ";".join(missing))
