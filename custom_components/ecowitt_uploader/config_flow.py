"""Config flow for the Ecowitt.net Uploader integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_INTERVAL,
    CONF_MAC,
    DEFAULT_INTERVAL,
    DOMAIN,
    FIELDS,
    MAX_INTERVAL,
    MIN_INTERVAL,
)
from .uploader import normalize_mac

INTERVAL_SELECTOR = selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=MIN_INTERVAL,
        max=MAX_INTERVAL,
        unit_of_measurement="s",
        mode=selector.NumberSelectorMode.BOX,
    )
)
SENSOR_SELECTOR = selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor"))

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MAC): selector.TextSelector(),
        vol.Required(CONF_INTERVAL, default=DEFAULT_INTERVAL): INTERVAL_SELECTOR,
    }
)
SENSORS_SCHEMA = vol.Schema({vol.Optional(field.key): SENSOR_SELECTOR for field in FIELDS})
OPTIONS_SCHEMA = vol.Schema(
    {vol.Required(CONF_INTERVAL, default=DEFAULT_INTERVAL): INTERVAL_SELECTOR}
).extend(SENSORS_SCHEMA.schema)


def _has_sensor(user_input: dict[str, Any]) -> bool:
    return any(user_input.get(field.key) for field in FIELDS)


class EcowittUploaderConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Set up uploads for one Ecowitt.net station."""

    VERSION = 1

    _mac: str
    _interval: int

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Ask for the station's MAC address and the upload interval."""
        errors: dict[str, str] = {}
        if user_input is not None:
            mac = normalize_mac(user_input[CONF_MAC])
            if mac is None:
                errors[CONF_MAC] = "invalid_mac"
            else:
                await self.async_set_unique_id(mac)
                self._abort_if_unique_id_configured()
                self._mac = mac
                self._interval = int(user_input[CONF_INTERVAL])
                return await self.async_step_sensors()

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Map Home Assistant sensors to the station's measurements."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if _has_sensor(user_input):
                return self.async_create_entry(
                    title=f"Ecowitt.net {self._mac}",
                    data={CONF_MAC: self._mac},
                    options={CONF_INTERVAL: self._interval, **user_input},
                )
            errors["base"] = "no_sensors"

        return self.async_show_form(
            step_id="sensors",
            data_schema=self.add_suggested_values_to_schema(SENSORS_SCHEMA, user_input),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> EcowittUploaderOptionsFlow:
        """Get the options flow for this handler."""
        return EcowittUploaderOptionsFlow()


class EcowittUploaderOptionsFlow(config_entries.OptionsFlow):
    """Change the interval and the sensor mapping."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Show the interval and every mapping in one form."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if _has_sensor(user_input):
                return self.async_create_entry(
                    data={**user_input, CONF_INTERVAL: int(user_input[CONF_INTERVAL])}
                )
            errors["base"] = "no_sensors"

        return self.async_show_form(
            step_id="init",
            # Suggested (not default) values, so clearing a sensor actually removes it.
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, user_input or self.config_entry.options
            ),
            errors=errors,
        )
