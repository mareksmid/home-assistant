from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant

from homeassistant.components.wallbox.coordinator import check_token_validity
from .coordinator import Wallbox2Coordinator, Wallbox2ConfigEntry

from .const import (
    CHARGER_JWT_REFRESH_TOKEN,
    CHARGER_JWT_REFRESH_TTL,
    CHARGER_JWT_TOKEN,
    CHARGER_JWT_TTL,
    UPDATE_INTERVAL,
)

from wallbox import Wallbox
from .const import DOMAIN, UPDATE_INTERVAL

PLATFORMS = [Platform.LOCK, Platform.NUMBER, Platform.SELECT, Platform.SENSOR, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: Wallbox2ConfigEntry) -> bool:
    wallbox = Wallbox(
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        jwtTokenDrift=UPDATE_INTERVAL,
    )
    if CHARGER_JWT_TOKEN in entry.data and check_token_validity(
            jwt_token_ttl=entry.data.get(CHARGER_JWT_TTL, 0),
            jwt_token_drift=UPDATE_INTERVAL,
    ):
        wallbox.jwtToken = entry.data.get(CHARGER_JWT_TOKEN)
        wallbox.jwtRefreshToken = entry.data.get(CHARGER_JWT_REFRESH_TOKEN)
        wallbox.jwtTokenTtl = entry.data.get(CHARGER_JWT_TTL)
        wallbox.jwtRefreshTokenTtl = entry.data.get(CHARGER_JWT_REFRESH_TTL)
        wallbox.headers["Authorization"] = f"Bearer {entry.data.get(CHARGER_JWT_TOKEN)}"

    wallbox_coordinator = Wallbox2Coordinator(hass, entry, wallbox)
    await wallbox_coordinator.async_config_entry_first_refresh()

    entry.runtime_data = wallbox_coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: Wallbox2ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
