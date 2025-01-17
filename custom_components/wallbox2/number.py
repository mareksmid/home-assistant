from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.exceptions import PlatformNotReady
from homeassistant.components.wallbox.coordinator import InvalidAuth
from homeassistant.components.wallbox.const import CHARGER_MAX_CHARGING_CURRENT_KEY
from homeassistant.components.wallbox.number import WallboxNumber, NUMBER_TYPES

from .coordinator import Wallbox2Coordinator
from .const import DOMAIN
from .entity import Wallbox2Entity


async def async_setup_entry(
        hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: Wallbox2Coordinator = hass.data[DOMAIN][entry.entry_id]
    try:
        await coordinator.async_set_charging_current(
            coordinator.data[CHARGER_MAX_CHARGING_CURRENT_KEY]
        )
    except InvalidAuth:
        return
    except ConnectionError as exc:
        raise PlatformNotReady from exc

    async_add_entities(
        Wallbox2Number(coordinator, entry, description)
        for ent in coordinator.data
        if (description := NUMBER_TYPES.get(ent))
    )

class Wallbox2Number(Wallbox2Entity, WallboxNumber):
    pass
