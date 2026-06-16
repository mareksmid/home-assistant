from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from homeassistant.components.wallbox.lock import WallboxLock, LOCK_TYPES
from .coordinator import Wallbox2Coordinator, Wallbox2ConfigEntry
from .const import DOMAIN
from .entity import Wallbox2Entity


async def async_setup_entry(
        hass: HomeAssistant, entry: Wallbox2ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator: Wallbox2Coordinator = entry.runtime_data
    async_add_entities(
        Wallbox2Lock(coordinator, description)
        for ent in coordinator.data
        if (description := LOCK_TYPES.get(ent))
    )


class Wallbox2Lock(Wallbox2Entity, WallboxLock):
    pass