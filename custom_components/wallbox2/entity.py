from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.wallbox.const import CHARGER_DATA_KEY, CHARGER_SERIAL_NUMBER_KEY, CHARGER_NAME_KEY, CHARGER_PART_NUMBER_KEY, CHARGER_SOFTWARE_KEY, CHARGER_CURRENT_VERSION_KEY
from .coordinator import Wallbox2Coordinator
from .const import DOMAIN

class Wallbox2Entity(CoordinatorEntity[Wallbox2Coordinator]):
    _attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    self.coordinator.data[CHARGER_DATA_KEY][CHARGER_SERIAL_NUMBER_KEY],
                )
            },
            name=f"Wallbox2 {self.coordinator.data[CHARGER_NAME_KEY]}",
            manufacturer="Wallbox",
            model=self.coordinator.data[CHARGER_NAME_KEY].split(" SN")[0],
            model_id=self.coordinator.data[CHARGER_DATA_KEY][CHARGER_PART_NUMBER_KEY],
            sw_version=self.coordinator.data[CHARGER_DATA_KEY][CHARGER_SOFTWARE_KEY][
                CHARGER_CURRENT_VERSION_KEY
            ],
        )
