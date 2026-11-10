"""Config flow for the Ecowitt.net Uploader integration.

Only supported Ecowitt stations (see profiles.py) seen over Bluetooth can be added; the
station's own Bluetooth address identifies it on ecowitt.net.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector

from .const import (
    CONF_INTERVAL,
    CONF_MAC,
    CONF_MODEL_ID,
    DEFAULT_INTERVAL,
    DOMAIN,
    MAX_INTERVAL,
    MIN_INTERVAL,
)
from .profiles import StationProfile, profile_for

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_INTERVAL, default=DEFAULT_INTERVAL): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=MIN_INTERVAL,
                max=MAX_INTERVAL,
                unit_of_measurement="s",
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
    }
)


class EcowittUploaderConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Add a supported Ecowitt station found over Bluetooth."""

    VERSION = 1

    def __init__(self) -> None:
        self._address = ""
        self._profile: StationProfile | None = None
        self._discovered: dict[str, StationProfile] = {}

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> config_entries.ConfigFlowResult:
        """A Shelly device was seen: continue only if it's a supported station."""
        profile = profile_for(discovery_info.manufacturer_data)
        if profile is None:
            return self.async_abort(reason="not_supported")
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._address, self._profile = discovery_info.address, profile
        self.context["title_placeholders"] = {"name": profile.name}
        return await self.async_step_confirm()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Pick one of the supported stations Home Assistant currently sees."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            self._address, self._profile = address, self._discovered[address]
            return await self.async_step_confirm()

        configured = self._async_current_ids(include_ignore=False)
        for info in async_discovered_service_info(self.hass, connectable=False):
            if info.address in configured:
                continue
            if profile := profile_for(info.manufacturer_data):
                self._discovered[info.address] = profile
        if not self._discovered:
            return self.async_abort(reason="no_devices_found")

        options = {addr: f"{p.name} ({addr})" for addr, p in self._discovered.items()}
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_ADDRESS): vol.In(options)}),
        )

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Show the MAC address to register on ecowitt.net and create the entry."""
        assert self._profile is not None
        placeholders = {"name": self._profile.name, "mac": self._address}

        if user_input is not None:
            # Checked only now: BTHome is often discovered at the same moment as this flow,
            # and aborting before showing the form would drop the discovery card for good.
            bthome_entity = er.async_get(self.hass).async_get_entity_id(
                "sensor", "bthome", f"{self._address}-temperature"
            )
            if bthome_entity is None:
                return self.async_abort(
                    reason="bthome_missing", description_placeholders=placeholders
                )
            return self.async_create_entry(
                title=f"Ecowitt.net {self._address}",
                data={CONF_MAC: self._address, CONF_MODEL_ID: self._profile.model_id},
                options={CONF_INTERVAL: DEFAULT_INTERVAL},
            )

        self._set_confirm_only()
        return self.async_show_form(step_id="confirm", description_placeholders=placeholders)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> EcowittUploaderOptionsFlow:
        """Get the options flow for this handler."""
        return EcowittUploaderOptionsFlow()


class EcowittUploaderOptionsFlow(config_entries.OptionsFlow):
    """Change the upload interval."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Show the interval."""
        if user_input is not None:
            return self.async_create_entry(data={CONF_INTERVAL: int(user_input[CONF_INTERVAL])})
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, self.config_entry.options
            ),
        )
