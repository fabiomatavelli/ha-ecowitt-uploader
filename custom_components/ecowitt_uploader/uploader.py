"""Ecowitt protocol upload to Ecowitt.net.

No Home Assistant imports: everything here is plain Python plus aiohttp, so it can be
tested without a running Home Assistant.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime

import aiohttp

UPLOAD_URL = "http://cdnrtpdate.ecowitt.net/data/report/"
STATION_TYPE = "HomeAssistant"
TIMEOUT = aiohttp.ClientTimeout(total=30)

_MAC_DIGITS = re.compile(r"[0-9A-Fa-f]{12}")


class UploadError(Exception):
    """Ecowitt.net refused or failed the upload."""


def normalize_mac(value: str) -> str | None:
    """Return ``AA:BB:CC:DD:EE:FF`` for any common MAC spelling, or None if invalid."""
    digits = re.sub(r"[\s:\-.]", "", value)
    if not _MAC_DIGITS.fullmatch(digits):
        return None
    digits = digits.upper()
    return ":".join(digits[i : i + 2] for i in range(0, 12, 2))


def passkey(mac: str) -> str:
    """Station key Ecowitt.net uses to match uploads to the registered device."""
    return hashlib.md5(mac.encode(), usedforsecurity=False).hexdigest().upper()


def sea_level_factor(elevation_m: float, temp_f: float | None) -> float:
    """Ratio sea-level/station pressure (hypsometric formula); 15 °C if no temperature."""
    temp_c = 15.0 if temp_f is None else (temp_f - 32) * 5 / 9
    lapse = 0.0065 * elevation_m
    return (1 - lapse / (temp_c + lapse + 273.15)) ** -5.257


def build_payload(
    mac: str, values: dict[str, float], now: datetime, elevation_m: float | None = None
) -> dict[str, str]:
    """Build the form fields for one upload.

    ``values`` maps Ecowitt parameters to numbers already in the protocol's units.
    Without a relative pressure, one is derived from the absolute pressure and
    ``elevation_m`` so Ecowitt.net doesn't leave it empty.
    """
    values = dict(values)
    if "baromrelin" not in values and "baromabsin" in values and elevation_m is not None:
        values["baromrelin"] = values["baromabsin"] * sea_level_factor(
            elevation_m, values.get("tempf")
        )
    return {
        "PASSKEY": passkey(mac),
        "stationtype": STATION_TYPE,
        "model": STATION_TYPE,
        "dateutc": now.strftime("%Y-%m-%d %H:%M:%S"),
        **{param: f"{value:.3f}".rstrip("0").rstrip(".") for param, value in values.items()},
    }


async def async_upload(session: aiohttp.ClientSession, payload: dict[str, str]) -> None:
    """POST one reading; raise UploadError unless Ecowitt.net answers ``errcode 0``."""
    try:
        async with session.post(UPLOAD_URL, data=payload, timeout=TIMEOUT) as resp:
            body = await resp.text()
    except (aiohttp.ClientError, TimeoutError) as err:
        raise UploadError(f"cannot reach Ecowitt.net: {err!r}") from err
    if resp.status != 200:
        raise UploadError(f"HTTP {resp.status}: {body[:200]}")
    try:
        result = json.loads(body)
    except ValueError as err:
        raise UploadError(f"unexpected response: {body[:200]}") from err
    if str(result.get("errcode")) != "0":
        raise UploadError(f"Ecowitt.net error {result.get('errcode')}: {result.get('errmsg')}")
