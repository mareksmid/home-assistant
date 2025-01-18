import logging
from itertools import groupby
from datetime import datetime, time, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.wallbox.sensor import WallboxSensor, SENSOR_TYPES
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, SensorStateClass, SensorDeviceClass
from homeassistant.components.recorder.statistics import async_import_statistics, DOMAIN as RECORDER_DOMAIN
from homeassistant.components.recorder.models import StatisticMetaData, StatisticData
from homeassistant.const import UnitOfEnergy
from homeassistant.util.dt import as_utc, DEFAULT_TIME_ZONE

from homeassistant.components.wallbox.const import CHARGER_DATA_KEY, CHARGER_SERIAL_NUMBER_KEY
from .coordinator import Wallbox2Coordinator
from .entity import Wallbox2Entity
from .const import DOMAIN, SESSION_ENERGY, SESSION_ATTRIBUTES, SESSION_TIME

_LOGGER = logging.getLogger(__name__)
HOUR_DELTA = timedelta(hours=1)


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
        self._attr_unique_id = f"{SESSION_ENERGY}4-{coordinator.data[CHARGER_DATA_KEY][CHARGER_SERIAL_NUMBER_KEY]}"

    @property
    def native_value(self) -> int|None:
        return None

    @property
    def native_unit_of_measurement(self) -> str | None:
        return self.entity_description.native_unit_of_measurement

    @staticmethod
    def _date_and_hour(timestamp: int):
        dt = datetime.fromtimestamp(timestamp)
        return dt.date(), dt.hour

    def _handle_coordinator_update(self) -> None:
        energy_sessions = self.coordinator.data[SESSION_ENERGY]
        if len(energy_sessions) > 0:
            total_energy = self.coordinator.data[SESSION_ENERGY + "_total"]
            entity_id = self.coordinator.data[SESSION_ENERGY + "_entity_id"]
            _LOGGER.warning(f"Saving {len(energy_sessions)} sessions from {total_energy}")

            stats = []
            for (day, hour), sessions in groupby(
                    sorted(energy_sessions, key=lambda s: s[SESSION_ATTRIBUTES][SESSION_TIME]),
                    key=lambda s: self._date_and_hour(s[SESSION_ATTRIBUTES][SESSION_TIME])
            ):
                energy = sum(s[SESSION_ATTRIBUTES][SESSION_ENERGY] for s in sessions)
                total_energy += energy
                stats.append(StatisticData(start=as_utc(datetime.combine(day, time(hour, 0, 0), tzinfo=DEFAULT_TIME_ZONE) - HOUR_DELTA), state=energy, sum=total_energy))
                _LOGGER.info(f"Stats @ {day}/{hour} = +{energy} -> {total_energy}")

            meta = StatisticMetaData(statistic_id=entity_id, source=RECORDER_DOMAIN, name='Total energy', has_sum=True, has_mean=False, unit_of_measurement=UnitOfEnergy.WATT_HOUR)
            async_import_statistics(self.coordinator._hass, meta, stats)
