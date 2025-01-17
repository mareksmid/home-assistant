from typing import Any
import requests
import json
import logging
from datetime import timedelta, datetime

from homeassistant.components.wallbox.coordinator import WallboxCoordinator, _require_authentication
from homeassistant.core import HomeAssistant, State
from homeassistant.components.wallbox.const import CHARGER_DATA_KEY, CHARGER_NAME_KEY
from homeassistant.helpers.translation import async_get_cached_translations
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.history import get_significant_states

from wallbox import Wallbox

from .const import SESSIONS_DATA, SESSION_ENERGY, CHARGER_GROUP_ID, DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class Wallbox2Coordinator(WallboxCoordinator):

    def __init__(self, station: str, wallbox: Wallbox, hass: HomeAssistant) -> None:
        self._hass = hass
        self._station = station
        self._wallbox = wallbox

        super(WallboxCoordinator, self).__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        if self.data is not None and CHARGER_NAME_KEY in self.data:
            translations = async_get_cached_translations(self._hass, self._hass.config.language, "entity_component")
            energy_name = translations[f"component.sensor.entity_component.{SESSION_ENERGY}.name"]
            energy_entity_id = f"sensor.{DOMAIN}_{self.data[CHARGER_NAME_KEY]}_{energy_name}_3".lower().replace(' ', '_')
            energy_state = self._hass.states.get(energy_entity_id)
            if energy_state is None or energy_state.state == 'unavailable' or energy_state.state == 'unknown':
                states = (await get_instance(self._hass).async_add_executor_job(
                    get_significant_states,
                    self._hass,
                    datetime.now() - timedelta(days=14),
                    None,
                    [energy_entity_id],
                    None,   # filters
                    True,   # include_start_time_state
                    True,   # significant_changes_only
                    False,  # minimal_response
                    True,   # no_attributes
                    False,  # compressed_state_format
                )).get(energy_entity_id, [])
                last_energy_state = max((s for s in states if s.state not in {"unknown", "unavailable"}), key=lambda s: s.last_changed, default=None)
                _LOGGER.warning(f"State none or not available, last is {last_energy_state}")
            else:
                last_energy_state = energy_state
        else:
            energy_entity_id = None
            last_energy_state = None
            _LOGGER.info("Skipping, as data not ready yet")
        return await self.hass.async_add_executor_job(self._get_data, energy_entity_id, last_energy_state)

    def _get_energy_sessions(self, group_id: str, start_time: int) -> list[dict[str, Any]]:
        end_time = int(datetime.now().timestamp())
        try:
            response = requests.get(
                f"{self._wallbox.baseUrl}v4/groups/{group_id}/charger-charging-sessions",
                params={
                    "filters": json.dumps({
                        "filters":[
                            {"field": "start_time", "operator": "gte", "value": start_time},
                            {"field": "start_time", "operator": "lt", "value": end_time},
                            {"field": "charger_id", "operator": "eq", "value": int(self._station)}          ,
                        ]
                    }),
                    "fields[charger_charging_session]": "",
                    "limit": 10000,
                    "offset": 0,
                },
                headers=self._wallbox.headers,
                timeout=self._wallbox._requestGetTimeout,
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise (err)

        r = json.loads(response.text)
        return r[SESSIONS_DATA]


    @_require_authentication
    def _get_data(self, energy_entity_id: str|None, last_energy_state: State|None) -> dict[str, Any]:
        data = super()._get_data()
        group_id = data[CHARGER_DATA_KEY][CHARGER_GROUP_ID]
        data[SESSION_ENERGY] = []
        if energy_entity_id is None:
            return data
        data[SESSION_ENERGY + "_entity_id"] = energy_entity_id

        if last_energy_state is None:
            start_time = 1704063600
            data[SESSION_ENERGY + "_total"] = 0
            _LOGGER.warning("Empty last state, starting from zero")
        else:
            start_time = int(last_energy_state.last_changed.timestamp()) + 1
            data[SESSION_ENERGY + "_total"] = int(last_energy_state.state)
            _LOGGER.info(f"Init state: {last_energy_state.state}")
        energy_sessions = self._get_energy_sessions(group_id, start_time)
        if len(energy_sessions) > 0:
            _LOGGER.info(f"Received {len(energy_sessions)} sessions")
        data[SESSION_ENERGY] = energy_sessions
        return data

# https://api.wall-box.com/v4/groups/428601/charger-charging-sessions
# group_id: 428601
# 443968
