from datetime import date, timedelta
from typing import Any

import httpx
from pypinyin import lazy_pinyin


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
DAILY_FIELDS = "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum"
WEATHER_CODES = {
    0: "晴",
    1: "大部晴朗",
    2: "局部多云",
    3: "阴",
    45: "雾",
    48: "雾凇",
    51: "毛毛雨",
    53: "毛毛雨",
    55: "强毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    80: "阵雨",
    81: "强阵雨",
    82: "暴雨",
    95: "雷暴",
    96: "雷暴伴冰雹",
    99: "强雷暴伴冰雹",
}


class Skill:
    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        print(f"weather skill parameters: {kwargs}")
        city = self._required_text(kwargs, "city")
        start_date = self._parse_date(kwargs, "start_date")
        end_date = self._parse_date(kwargs, "end_date")
        if start_date > end_date:
            raise ValueError("start_date must be on or before end_date")

        async with httpx.AsyncClient(timeout=15.0) as client:
            location = await self._find_location(client, city)
            daily = await self._fetch_daily_weather(client, location, start_date, end_date)

        return {
            "city": location["name"],
            "country": location.get("country"),
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "daily": daily,
        }

    @staticmethod
    def _required_text(kwargs: dict[str, Any], field: str) -> str:
        value = kwargs.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty string")
        return value.strip()

    @staticmethod
    def _parse_date(kwargs: dict[str, Any], field: str) -> date:
        value = kwargs.get(field)
        if not isinstance(value, str):
            raise ValueError(f"{field} must be an ISO date string (YYYY-MM-DD)")
        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise ValueError(f"{field} must be an ISO date string (YYYY-MM-DD)") from error

    async def _find_location(
        self, client: httpx.AsyncClient, city: str
    ) -> dict[str, Any]:
        for name in (city, self._pinyin_city_name(city)):
            response = await client.get(GEOCODING_URL, params={"name": name, "count": 1})
            response.raise_for_status()
            results = response.json().get("results", [])
            if results:
                return results[0]
        raise ValueError(f"No location found for city: {city}")

    @staticmethod
    def _pinyin_city_name(city: str) -> str:
        return "".join(lazy_pinyin(city)).title()

    async def _fetch_daily_weather(
        self,
        client: httpx.AsyncClient,
        location: dict[str, Any],
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        today = date.today()
        requests: list[tuple[str, date, date]] = []
        if start_date < today:
            requests.append((ARCHIVE_URL, start_date, min(end_date, today - timedelta(days=1))))
        if end_date >= today:
            requests.append((FORECAST_URL, max(start_date, today), end_date))

        daily: list[dict[str, Any]] = []
        for url, range_start, range_end in requests:
            response = await client.get(
                url,
                params={
                    "latitude": location["latitude"],
                    "longitude": location["longitude"],
                    "start_date": range_start.isoformat(),
                    "end_date": range_end.isoformat(),
                    "daily": DAILY_FIELDS,
                    "timezone": "auto",
                },
            )
            response.raise_for_status()
            daily.extend(self._normalize_daily(response.json().get("daily", {})))
        return daily

    @staticmethod
    def _normalize_daily(payload: dict[str, list[Any]]) -> list[dict[str, Any]]:
        return [
            {
                "date": day,
                "weather": WEATHER_CODES.get(code, "未知"),
                "weather_code": code,
                "temperature_max_c": maximum,
                "temperature_min_c": minimum,
                "precipitation_mm": precipitation,
            }
            for day, code, maximum, minimum, precipitation in zip(
                payload.get("time", []),
                payload.get("weather_code", []),
                payload.get("temperature_2m_max", []),
                payload.get("temperature_2m_min", []),
                payload.get("precipitation_sum", []),
                strict=True,
            )
        ]