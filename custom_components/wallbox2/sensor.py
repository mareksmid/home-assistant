import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.wallbox.sensor import WallboxSensor, SENSOR_TYPES
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, SensorStateClass, SensorDeviceClass
from homeassistant.const import UnitOfEnergy

from homeassistant.components.wallbox.const import CHARGER_DATA_KEY, CHARGER_SERIAL_NUMBER_KEY
from .coordinator import Wallbox2Coordinator
from .entity import Wallbox2Entity
from .const import DOMAIN, SESSION_ENERGY, SESSION_ATTRIBUTES, SESSION_TIME

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: Wallbox2Coordinator = hass.data[DOMAIN][entry.entry_id]

    sensors: list[SensorEntity] = [
        Wallbox2Sensor(coordinator, description)
        for ent in coordinator.data
        if (description := SENSOR_TYPES.get(ent))
    ]
    sensors.append(WallboxEnergySensor(coordinator))
    async_add_entities(sensors)


class Wallbox2Sensor(Wallbox2Entity, WallboxSensor):
    pass


class WallboxEnergySensor(Wallbox2Entity, SensorEntity):

    def __init__(self, coordinator: Wallbox2Coordinator) -> None:
        super().__init__(coordinator)
        self.entity_description = SensorEntityDescription(
            key=SESSION_ENERGY,
            translation_key=SESSION_ENERGY,
            native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
        )
        self._attr_unique_id = f"{SESSION_ENERGY}3-{coordinator.data[CHARGER_DATA_KEY][CHARGER_SERIAL_NUMBER_KEY]}"

    @property
    def native_value(self) -> int|None:
        return None

    @property
    def native_unit_of_measurement(self) -> str | None:
        return self.entity_description.native_unit_of_measurement

    def _handle_coordinator_update(self) -> None:
        energy_sessions = self.coordinator.data[SESSION_ENERGY]
        if len(energy_sessions) > 0:
            total_energy = self.coordinator.data[SESSION_ENERGY + "_total"]
            entity_id = self.coordinator.data[SESSION_ENERGY + "_entity_id"]
            _LOGGER.warning(f"Saving {len(energy_sessions)} sessions from {total_energy}")

            for session in sorted(energy_sessions, key=lambda s: s[SESSION_ATTRIBUTES][SESSION_TIME]):
                total_energy += session[SESSION_ATTRIBUTES][SESSION_ENERGY]
                time = session[SESSION_ATTRIBUTES][SESSION_TIME]
                self.coordinator._hass.states.async_set(entity_id, str(total_energy), timestamp=float(time), attributes={"unit_of_measurement": UnitOfEnergy.WATT_HOUR})
