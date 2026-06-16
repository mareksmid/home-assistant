from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.components.wallbox.number import WallboxNumber, NUMBER_TYPES

from .coordinator import Wallbox2Coordinator, Wallbox2ConfigEntry
from .entity import Wallbox2Entity


async def async_setup_entry(
        hass: HomeAssistant, entry: Wallbox2ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator: Wallbox2Coordinator = entry.runtime_data
    async_add_entities(
        Wallbox2Number(coordinator, entry, description)
        for ent in coordinator.data
        if (description := NUMBER_TYPES.get(ent))
    )

class Wallbox2Number(Wallbox2Entity, WallboxNumber):
    pass
