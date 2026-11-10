"""Config and options flow."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ecowitt_uploader.const import CONF_INTERVAL, CONF_MAC, DOMAIN

from .conftest import MAC


@pytest.fixture(autouse=True)
def no_setup() -> Generator[None]:
    """Don't upload while testing the flow."""
    with patch("custom_components.ecowitt_uploader.async_setup_entry", return_value=True):
        yield


async def test_full_flow(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_MAC: "aa-bb-cc-dd-ee-ff", CONF_INTERVAL: 120}
    )
    assert result["step_id"] == "sensors"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["errors"] == {"base": "no_sensors"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"temperature": "sensor.temp"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"Ecowitt.net {MAC}"
    assert result["data"] == {CONF_MAC: MAC}
    assert result["options"] == {CONF_INTERVAL: 120, "temperature": "sensor.temp"}
    assert result["result"].unique_id == MAC


async def test_invalid_mac(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_MAC: "not-a-mac", CONF_INTERVAL: 60}
    )
    assert result["errors"] == {CONF_MAC: "invalid_mac"}


async def test_already_configured(hass: HomeAssistant) -> None:
    MockConfigEntry(domain=DOMAIN, unique_id=MAC, data={CONF_MAC: MAC}).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_MAC: MAC.lower(), CONF_INTERVAL: 60}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow_replaces_mapping(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MAC,
        data={CONF_MAC: MAC},
        options={CONF_INTERVAL: 60, "temperature": "sensor.temp", "humidity": "sensor.hum"},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_INTERVAL: 300}
    )
    assert result["errors"] == {"base": "no_sensors"}

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_INTERVAL: 300, "temperature": "sensor.other"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {CONF_INTERVAL: 300, "temperature": "sensor.other"}
