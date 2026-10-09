from UM.Extension import Extension
from UM.Logger import Logger
from UM.Settings.SettingDefinition import SettingDefinition
from cura.CuraApplication import CuraApplication

SETTING_KEY = "inset_direction"
OPTION_ID = "inner_outer_inner"
OPTION_LABEL = "Inner/Outer/Inner"


def _add_option(definition: SettingDefinition) -> bool:
    if definition.key != SETTING_KEY or OPTION_ID in definition.options:
        return False
    definition.extend_category(OPTION_ID, OPTION_LABEL)
    return True


class InnerOuterInnerWalls(Extension):
    def __init__(self) -> None:
        super().__init__()
        self._patch_definition_parsing()
        application = CuraApplication.getInstance()
        application.globalContainerStackChanged.connect(self._patch_active_machine)

    @staticmethod
    def _patch_definition_parsing() -> None:
        """Every definition container parses its own copy of the setting, so hook the parser itself."""
        if getattr(SettingDefinition, "_ioi_patched", False):
            return
        original = SettingDefinition._deserialize_dict

        def patched(self, serialized):
            original(self, serialized)
            try:
                _add_option(self)
            except Exception as e:
                Logger.log("e", "Inner/Outer/Inner: could not add option: %s", e)

        SettingDefinition._deserialize_dict = patched
        SettingDefinition._ioi_patched = True
        Logger.log("i", "Inner/Outer/Inner: hooked setting definition parsing")

    def _patch_active_machine(self) -> None:
        """Make sure the printer that is active right now offers the option, and log what the settings panel will see."""
        try:
            stack = CuraApplication.getInstance().getGlobalContainerStack()
            if stack is None:
                return
            for definition in stack.definition.findDefinitions(key = SETTING_KEY):
                added = _add_option(definition)
                Logger.log("i", "Inner/Outer/Inner: printer '%s' offers wall ordering options %s (added now: %s)",
                           stack.getName(), list(definition.options.keys()), added)
        except Exception as e:
            Logger.log("e", "Inner/Outer/Inner: could not check the active printer: %s", e)
