from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from homeassistant.components.wallbox.switch import SWITCH_TYPES, WallboxSwitch
from homeassistant.components.wallbox.const import CHARGER_PAUSE_RESUME_KEY
from .coordinator import Wallbox2Coordinator, Wallbox2ConfigEntry
from .entity import Wallbox2Entity


async def async_setup_entry(
        hass: HomeAssistant, entry: Wallbox2ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator: Wallbox2Coordinator = entry.runtime_data
    async_add_entities(
        [Wallbox2Switch(coordinator, SWITCH_TYPES[CHARGER_PAUSE_RESUME_KEY])]
    )


class Wallbox2Switch(Wallbox2Entity, WallboxSwitch):
    pass
