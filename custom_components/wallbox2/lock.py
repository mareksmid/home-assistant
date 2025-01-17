from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from homeassistant.components.wallbox.lock import WallboxLock, LOCK_TYPES
from homeassistant.components.wallbox.const import CHARGER_LOCKED_UNLOCKED_KEY
from homeassistant.components.wallbox.coordinator import InvalidAuth
from .coordinator import Wallbox2Coordinator
from .const import DOMAIN
from .entity import Wallbox2Entity


async def async_setup_entry(
        hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: Wallbox2Coordinator = hass.data[DOMAIN][entry.entry_id]
    try:
        await coordinator.async_set_lock_unlock(
            coordinator.data[CHARGER_LOCKED_UNLOCKED_KEY]
        )
    except InvalidAuth:
        return
    except ConnectionError as exc:
        raise PlatformNotReady from exc

    async_add_entities(
        Wallbox2Lock(coordinator, description)
        for ent in coordinator.data
        if (description := LOCK_TYPES.get(ent))
    )


class Wallbox2Lock(Wallbox2Entity, WallboxLock):
    pass