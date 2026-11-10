"""Pure protocol helpers: MAC handling, passkey and payload."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from custom_components.ecowitt_uploader.uploader import (
    build_payload,
    passkey,
    sea_level_factor,
)

from .conftest import MAC, PASSKEY

NOW = datetime(2026, 11, 10, 10, 48, 0, tzinfo=UTC)


def test_passkey() -> None:
    assert passkey(MAC) == PASSKEY


def test_build_payload_formats_fields() -> None:
    payload = build_payload(
        MAC, {"tempf": 66.2, "humidity": 90.0, "uv": 0.0, "baromabsin": 29.6067612}, NOW
    )
    assert payload == {
        "PASSKEY": PASSKEY,
        "stationtype": "HomeAssistant",
        "model": "HomeAssistant",
        "dateutc": "2026-11-10 10:48:00",
        "tempf": "66.2",
        "humidity": "90",
        "uv": "0",
        "baromabsin": "29.607",
    }


def test_relative_pressure_derived_from_elevation() -> None:
    values = {"baromabsin": 29.0, "tempf": 59.0}
    assert "baromrelin" not in build_payload(MAC, values, NOW)
    assert build_payload(MAC, values, NOW, elevation_m=0)["baromrelin"] == "29"
    # ~12 hPa per 100 m near sea level at 15 °C
    assert sea_level_factor(100, 59.0) == pytest.approx(1.0119, abs=1e-4)
    assert sea_level_factor(100, None) == sea_level_factor(100, 59.0)


def test_mapped_relative_pressure_wins() -> None:
    payload = build_payload(MAC, {"baromabsin": 29.0, "baromrelin": 30.0}, NOW, elevation_m=500)
    assert payload["baromrelin"] == "30"
