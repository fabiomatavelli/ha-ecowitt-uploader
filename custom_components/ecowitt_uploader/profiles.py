"""Supported Ecowitt stations and how their Bluetooth readings map to the Ecowitt protocol.

Only stations listed in ``PROFILES`` can be set up: ecowitt.net is fed by Ecowitt hardware,
so this integration only uploads readings that come from an Ecowitt station.

Stations are recognised by the model ID in their Bluetooth advertisement (Shelly/Allterco
manufacturer data, company ID 0x0BA9) and read through the entities Home Assistant's BTHome
integration creates for them. BTHome entity unique IDs are ``<MAC>-<key>``; ``sensors``
maps those keys to Ecowitt protocol parameters.

No I/O here.
"""

from __future__ import annotations

from typing import NamedTuple

SHELLY_COMPANY_ID = 0x0BA9

# Block type -> payload length in Shelly's manufacturer data.
_BLOCK_FLAGS = 0x01
_BLOCK_MAC = 0x0A
_BLOCK_MODEL = 0x0B
_BLOCK_SIZES = {_BLOCK_FLAGS: 2, _BLOCK_MAC: 6, _BLOCK_MODEL: 2}


class StationProfile(NamedTuple):
    """One supported station model."""

    model_id: int
    name: str
    sensors: dict[str, str]  # BTHome key -> Ecowitt parameter
    rain_total: str | None  # BTHome key of the station's accumulated rain, in mm


# Ecowitt WS90 sold by Shelly as SBWS-90CM ("Ecowitt WS90 - Weather Station" in Shelly's BLE
# docs). Verified against a live station: model ID 0x000B in the manufacturer data, BTHome
# device type 11. It broadcasts wind and gust as two speed objects (speed_1, speed_2) and
# rain only as an accumulated total, no rain rate.
WS90 = StationProfile(
    model_id=0x000B,
    name="Ecowitt WS90 (Shelly SBWS-90CM)",
    sensors={
        "temperature": "tempf",
        "humidity": "humidity",
        "pressure": "baromabsin",
        "speed_1": "windspeedmph",
        "speed_2": "windgustmph",
        "direction": "winddir",
        "uv_index": "uv",
        "illuminance": "solarradiation",
    },
    rain_total="precipitation",
)

PROFILES: dict[int, StationProfile] = {WS90.model_id: WS90}


def parse_shelly_model_id(manufacturer_data: dict[int, bytes]) -> int | None:
    """Model ID from Shelly manufacturer data, or None if absent or malformed."""
    data = manufacturer_data.get(SHELLY_COMPANY_ID)
    if not data:
        return None
    i = 0
    while i < len(data):
        size = _BLOCK_SIZES.get(data[i])
        if size is None:  # unknown block: its length is unknown too, stop
            return None
        block = data[i + 1 : i + 1 + size]
        if len(block) < size:
            return None
        if data[i] == _BLOCK_MODEL:
            return int.from_bytes(block, "little")
        i += 1 + size
    return None


def profile_for(manufacturer_data: dict[int, bytes]) -> StationProfile | None:
    """The supported station advertising this data, if any."""
    model_id = parse_shelly_model_id(manufacturer_data)
    return None if model_id is None else PROFILES.get(model_id)
