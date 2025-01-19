from typing import Any
import requests
import json
import logging
from datetime import timedelta, datetime

from homeassistant.components.wallbox.coordinator import WallboxCoordinator, _require_authentication
from homeassistant.core import HomeAssistant
from homeassistant.components.wallbox.const import CHARGER_DATA_KEY, CHARGER_NAME_KEY
from homeassistant.helpers.translation import async_get_cached_translations
from homeassistant.util.dt import utcnow, utc_from_timestamp
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import get_last_statistics

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
            energy_entity_id = f"sensor.{DOMAIN}_{self.data[CHARGER_NAME_KEY]}_{energy_name}_4".lower().replace(' ', '_')

            last_energy_stats = await get_instance(self._hass).async_add_executor_job(
                get_last_statistics,
                self._hass,
                1,
                energy_entity_id,
                False,
                {"sum"},
            )
            if len(last_energy_stats) == 0:
                last_energy_stats_date = None
                last_energy_stats_sum = None
                _LOGGER.warning(f"Energy stats not available, starting from zero")
            else:
                les = last_energy_stats[energy_entity_id][0]
                last_energy_stats_date = utc_from_timestamp(les['end'])
                last_energy_stats_sum = les['sum']
                _LOGGER.info(f'Last energy stats: {les}')
        else:
            energy_entity_id = None
            last_energy_stats_date = None
            last_energy_stats_sum = None
            _LOGGER.info("Skipping, as data not ready yet")
        return await self.hass.async_add_executor_job(self._get_data, energy_entity_id, last_energy_stats_date, last_energy_stats_sum)

    def _get_energy_sessions(self, group_id: str, start_time: int) -> list[dict[str, Any]]:
        last_hour_end = utcnow().replace(minute=0, second=0, microsecond=0)
        end_time = int(last_hour_end.timestamp())
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
            raise err

        r = json.loads(response.text)
        return r[SESSIONS_DATA]


    @_require_authentication
    def _get_data(self, energy_entity_id: str|None, last_energy_stats_date: datetime|None, last_energy_stats_sum: int|None) -> dict[str, Any]:
        data = super()._get_data()
        group_id = data[CHARGER_DATA_KEY][CHARGER_GROUP_ID]
        data[SESSION_ENERGY] = []
        if energy_entity_id is None:
            return data
        data[SESSION_ENERGY + "_entity_id"] = energy_entity_id

        if last_energy_stats_sum is None:
            start_time = 1704063600
            data[SESSION_ENERGY + "_total"] = 0
            _LOGGER.warning("Empty last state, starting from zero")
        else:
            start_time = int(last_energy_stats_date.timestamp())
            data[SESSION_ENERGY + "_total"] = int(last_energy_stats_sum)
            _LOGGER.info(f"Init stats: {last_energy_stats_sum} @ {last_energy_stats_date}")
        energy_sessions = self._get_energy_sessions(group_id, start_time)
        if len(energy_sessions) > 0:
            _LOGGER.info(f"Received {len(energy_sessions)} sessions")
        data[SESSION_ENERGY] = energy_sessions
        return data

# https://api.wall-box.com/v4/groups/428601/charger-charging-sessions
# group_id: 428601
# 443968
