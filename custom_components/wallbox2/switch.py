from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from homeassistant.components.wallbox.switch import SWITCH_TYPES, WallboxSwitch
from homeassistant.components.wallbox.const import CHARGER_PAUSE_RESUME_KEY
from .coordinator import Wallbox2Coordinator
from .const import DOMAIN
from .entity import Wallbox2Entity


async def async_setup_entry(
        hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: Wallbox2Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [Wallbox2Switch(coordinator, SWITCH_TYPES[CHARGER_PAUSE_RESUME_KEY])]
    )


class Wallbox2Switch(Wallbox2Entity, WallboxSwitch):
    pass
