"""Period rain totals and rate from an accumulated total."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import flush_store

from custom_components.ecowitt_uploader.rain import RainTracker

# Wednesday
T0 = datetime(2026, 11, 11, 10, 0)


async def test_periods_start_at_zero_and_accumulate(hass: HomeAssistant) -> None:
    rain = RainTracker(hass, "e1")
    first = rain.update(40.0, T0)
    assert {k: v for k, v in first.items()} == {
        "dailyrainin": 0,
        "weeklyrainin": 0,
        "monthlyrainin": 0,
        "yearlyrainin": 0,
        "rainratein": 0,
    }
    later = rain.update(42.5, T0 + timedelta(hours=2))
    assert later["dailyrainin"] == pytest.approx(2.5)
    assert later["yearlyrainin"] == pytest.approx(2.5)


async def test_rollovers(hass: HomeAssistant) -> None:
    rain = RainTracker(hass, "e1")
    rain.update(10.0, T0)
    rain.update(11.0, T0 + timedelta(hours=1))
    next_day = rain.update(12.0, datetime(2026, 11, 12, 0, 5))
    assert next_day["dailyrainin"] == 0
    assert next_day["weeklyrainin"] == pytest.approx(2.0)
    # Sunday 2026-11-15 starts a new week, December a new month, 2027 a new year
    assert rain.update(13.0, datetime(2026, 11, 15, 8, 0))["weeklyrainin"] == 0
    assert rain.update(14.0, datetime(2026, 12, 1, 8, 0))["monthlyrainin"] == 0
    new_year = rain.update(15.0, datetime(2027, 1, 1, 8, 0))
    assert new_year["yearlyrainin"] == 0
    assert rain.update(16.0, datetime(2027, 1, 1, 9, 0))["yearlyrainin"] == pytest.approx(1.0)


async def test_counter_reset_keeps_counting(hass: HomeAssistant) -> None:
    rain = RainTracker(hass, "e1")
    rain.update(6550.0, T0)
    rain.update(6553.0, T0 + timedelta(minutes=30))
    after_wrap = rain.update(1.0, T0 + timedelta(hours=1))  # wrapped to 1 mm
    assert after_wrap["dailyrainin"] == pytest.approx(4.0)


async def test_rate_over_last_ten_minutes(hass: HomeAssistant) -> None:
    rain = RainTracker(hass, "e1")
    for minute in range(0, 31):  # 0.1 per minute = 6 per hour
        result = rain.update(minute * 0.1, T0 + timedelta(minutes=minute))
    assert result["rainratein"] == pytest.approx(6.0)
    dry = rain.update(3.0, T0 + timedelta(minutes=45))
    assert dry["rainratein"] == 0


async def test_state_survives_restart(hass: HomeAssistant, hass_storage: dict) -> None:
    rain = RainTracker(hass, "e1")
    rain.update(20.0, T0)
    rain.update(25.0, T0 + timedelta(hours=1))
    await flush_store(rain._store)

    restored = RainTracker(hass, "e1")
    await restored.async_load()
    assert restored.update(26.0, T0 + timedelta(hours=2))["dailyrainin"] == pytest.approx(6.0)
