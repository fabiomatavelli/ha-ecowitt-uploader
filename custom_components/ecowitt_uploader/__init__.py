"""The Ecowitt.net Uploader integration."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import EcowittUploadCoordinator, EcowittUploaderConfigEntry
from .rain import rain_store

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: EcowittUploaderConfigEntry) -> bool:
    """Start uploading the station's readings."""
    coordinator = EcowittUploadCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    # The coordinator only schedules refreshes while it has listeners: keep uploading
    # even if the user disables the status sensor.
    entry.async_on_unload(coordinator.async_add_listener(lambda: None))
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EcowittUploaderConfigEntry) -> bool:
    """Stop uploading."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: EcowittUploaderConfigEntry) -> None:
    """Delete the saved rain period starts along with the entry."""
    await rain_store(hass, entry.entry_id).async_remove()


async def _async_update_listener(hass: HomeAssistant, entry: EcowittUploaderConfigEntry) -> None:
    """Reload so a new upload interval takes effect."""
    await hass.config_entries.async_reload(entry.entry_id)
