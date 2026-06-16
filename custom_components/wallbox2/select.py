from homeassistant.components.wallbox.select import WallboxSelect, SELECT_TYPES
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from custom_components.wallbox2.const import CHARGER_ECO_SMART_KEY, EcoSmartMode
from custom_components.wallbox2.coordinator import Wallbox2Coordinator, Wallbox2ConfigEntry
from custom_components.wallbox2.entity import Wallbox2Entity


async def async_setup_entry(
        hass: HomeAssistant,
        entry: Wallbox2ConfigEntry,
        async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator: Wallbox2Coordinator = entry.runtime_data
    if coordinator.data[CHARGER_ECO_SMART_KEY] != EcoSmartMode.DISABLED:
        async_add_entities(
            Wallbox2Select(coordinator, description)
            for ent in coordinator.data
            if (
                    (description := SELECT_TYPES.get(ent))
                    and description.supported_fn(coordinator)
            )
        )

class Wallbox2Select(Wallbox2Entity, WallboxSelect):
    pass