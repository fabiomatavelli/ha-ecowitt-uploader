"""Daily/weekly/monthly/yearly rain and rain rate from a station's accumulated rain total.

Stations like the WS90 only broadcast an ever-growing total. Ecowitt.net expects per-period
totals, so each period's starting total is remembered (and persisted) and subtracted. Works
in whatever unit it's fed; the coordinator feeds inches.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

RATE_WINDOW = timedelta(minutes=10)
SAVE_DELAY = 30


def _week_start(day: date) -> date:
    """Weeks start on Sunday, like on Ecowitt gateways."""
    return day - timedelta(days=(day.weekday() + 1) % 7)


PERIODS: dict[str, Callable[[datetime], str]] = {
    "dailyrainin": lambda now: now.date().isoformat(),
    "weeklyrainin": lambda now: _week_start(now.date()).isoformat(),
    "monthlyrainin": lambda now: f"{now.year}-{now.month:02d}",
    "yearlyrainin": lambda now: str(now.year),
}


class RainTracker:
    """Turns an accumulated rain total into Ecowitt's period totals and rate."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, 1, f"{DOMAIN}.{entry_id}.rain")
        self._state: dict[str, Any] = {"offset": 0.0, "last_total": None, "bases": {}}
        self._history: deque[tuple[datetime, float]] = deque()

    async def async_load(self) -> None:
        """Restore period starts saved before a restart."""
        if stored := await self._store.async_load():
            self._state = stored

    def update(self, total: float, now: datetime) -> dict[str, float]:
        """Period totals and rate (per hour) for the station's current total.

        ``now`` must be local time, so periods roll over at local midnight. A period first
        seen mid-way (fresh install) starts from zero.
        """
        state = self._state
        last = state["last_total"]
        if last is not None and total < last:  # counter reset or wrapped: keep counting up
            state["offset"] += last
        state["last_total"] = total
        accumulated = state["offset"] + total

        result: dict[str, float] = {}
        for param, period_of in PERIODS.items():
            period = period_of(now)
            base = state["bases"].get(param)
            if base is None or base[0] != period:
                base = state["bases"][param] = [period, accumulated]
            result[param] = accumulated - base[1]

        self._history.append((now, accumulated))
        while len(self._history) > 1 and self._history[1][0] <= now - RATE_WINDOW:
            self._history.popleft()
        start, start_total = self._history[0]
        hours = max(now - start, RATE_WINDOW).total_seconds() / 3600
        result["rainratein"] = (accumulated - start_total) / hours

        self._store.async_delay_save(lambda: self._state, SAVE_DELAY)
        return result
