"""Status sensor: when the station was last uploaded to Ecowitt.net."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EcowittUploadCoordinator, EcowittUploaderConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EcowittUploaderConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the last-upload sensor."""
    async_add_entities([LastUploadSensor(entry.runtime_data)])


class LastUploadSensor(CoordinatorEntity[EcowittUploadCoordinator], SensorEntity):
    """Time of the last accepted upload; unavailable while uploads are failing."""

    _attr_has_entity_name = True
    _attr_translation_key = "last_upload"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: EcowittUploadCoordinator) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.unique_id}_last_upload"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name=entry.title,
            manufacturer="Ecowitt.net",
            model=coordinator.profile.name,
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://www.ecowitt.net",
        )

    @property
    def native_value(self) -> datetime:
        return self.coordinator.data.uploaded_at

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"fields": self.coordinator.data.params}
