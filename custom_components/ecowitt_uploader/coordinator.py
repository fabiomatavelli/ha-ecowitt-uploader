"""Periodic upload of the mapped sensors to Ecowitt.net."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    LIGHT_LUX,
    UnitOfIrradiance,
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfVolumetricFlux,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_conversion import (
    BaseUnitConverter,
    DistanceConverter,
    PressureConverter,
    SpeedConverter,
    TemperatureConverter,
)

from .const import CONF_INTERVAL, CONF_MAC, DEFAULT_INTERVAL, DOMAIN, FIELDS
from .uploader import UploadError, async_upload, build_payload

_LOGGER = logging.getLogger(__name__)

# Ecowitt.net shows solar radiation as lux using this factor, so it's the one to undo.
LUX_PER_W_M2 = 126.7

IDENTITY_PARAMS = {"PASSKEY", "stationtype", "model", "dateutc"}

CONVERTERS: dict[str, type[BaseUnitConverter]] = {
    UnitOfTemperature.FAHRENHEIT: TemperatureConverter,
    UnitOfPressure.INHG: PressureConverter,
    UnitOfSpeed.MILES_PER_HOUR: SpeedConverter,
    UnitOfVolumetricFlux.INCHES_PER_HOUR: SpeedConverter,
    UnitOfPrecipitationDepth.INCHES: DistanceConverter,
}


@dataclass(frozen=True)
class UploadStatus:
    """Result of the last successful upload."""

    uploaded_at: datetime
    params: list[str]


def convert(value: float, from_unit: str | None, to_unit: str | None) -> float | None:
    """Convert to the protocol's unit, or None if the source unit isn't usable."""
    if to_unit is None:
        return value
    if to_unit == UnitOfIrradiance.WATTS_PER_SQUARE_METER:
        if from_unit == LIGHT_LUX:
            return value / LUX_PER_W_M2
        return value if from_unit == to_unit else None
    converter = CONVERTERS[to_unit]
    if from_unit not in converter.VALID_UNITS:
        return None
    return converter.convert(value, from_unit, to_unit)


type EcowittUploaderConfigEntry = ConfigEntry[EcowittUploadCoordinator]


class EcowittUploadCoordinator(DataUpdateCoordinator[UploadStatus]):
    """Reads the mapped sensors and uploads them every ``interval`` seconds."""

    config_entry: EcowittUploaderConfigEntry

    def __init__(self, hass: HomeAssistant, entry: EcowittUploaderConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=entry.options.get(CONF_INTERVAL, DEFAULT_INTERVAL)),
        )
        self._session = async_get_clientsession(hass)

    def read_values(self) -> dict[str, float]:
        """Current value of each mapped sensor, in protocol units, keyed by parameter."""
        values: dict[str, float] = {}
        for field in FIELDS:
            entity_id = self.config_entry.options.get(field.key)
            state = self.hass.states.get(entity_id) if entity_id else None
            if state is None:
                continue
            try:
                raw = float(state.state)
            except ValueError:  # unknown / unavailable / non-numeric
                continue
            unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            value = convert(raw, unit, field.unit)
            if value is None:
                _LOGGER.debug("Skipping %s: unit %r can't be converted", entity_id, unit)
                continue
            values[field.param] = value
        return values

    async def _async_update_data(self) -> UploadStatus:
        values = self.read_values()
        if not values:
            raise UpdateFailed("None of the mapped sensors has a usable value")
        now = dt_util.utcnow()
        payload = build_payload(
            self.config_entry.data[CONF_MAC], values, now, self.hass.config.elevation
        )
        try:
            await async_upload(self._session, payload)
        except UploadError as err:
            raise UpdateFailed(str(err)) from err
        return UploadStatus(uploaded_at=now, params=sorted(payload.keys() - IDENTITY_PARAMS))
