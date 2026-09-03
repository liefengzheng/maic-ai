import importlib.util
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch


SKILL_PATH = Path(__file__).resolve().parents[1] / "app" / "runtime" / "skills" / "weather" / "skill.py"
SPEC = importlib.util.spec_from_file_location("weather_skill", SKILL_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
Skill = MODULE.Skill


class WeatherSkillTests(unittest.IsolatedAsyncioTestCase):
    def test_normalizes_open_meteo_daily_response(self) -> None:
        result = Skill._normalize_daily({
            "time": ["2026-09-01"],
            "weather_code": [61],
            "temperature_2m_max": [28.5],
            "temperature_2m_min": [21.0],
            "precipitation_sum": [3.2],
        })

        self.assertEqual(result, [{
            "date": "2026-09-01",
            "weather": "小雨",
            "weather_code": 61,
            "temperature_max_c": 28.5,
            "temperature_min_c": 21.0,
            "precipitation_mm": 3.2,
        }])

    async def test_rejects_a_reversed_date_range_before_network_access(self) -> None:
        with self.assertRaisesRegex(ValueError, "start_date must be on or before"):
            await Skill().execute(city="北京", start_date="2026-09-02", end_date="2026-09-01")

    async def test_retries_chinese_city_name_with_pinyin_when_not_found(self) -> None:
        empty_response = unittest.mock.Mock()
        empty_response.json.return_value = {}
        location_response = unittest.mock.Mock()
        location_response.json.return_value = {
            "results": [{"name": "Dalian", "latitude": 38.9, "longitude": 121.6}]
        }
        client = unittest.mock.Mock()
        client.get = AsyncMock(side_effect=[empty_response, location_response])

        location = await Skill()._find_location(client, "大连")

        self.assertEqual(location["name"], "Dalian")
        self.assertEqual(client.get.await_args_list[1].kwargs["params"]["name"], "Dalian")

    async def test_splits_a_range_at_today(self) -> None:
        skill = Skill()
        response = unittest.mock.Mock()
        response.json.return_value = {"daily": {}}
        client = unittest.mock.Mock()
        client.get = AsyncMock(return_value=response)
        location = {"latitude": 39.9, "longitude": 116.4}
        today = date.today()

        with patch.object(skill, "_normalize_daily", return_value=[]):
            await skill._fetch_daily_weather(
                client,
                location,
                today - timedelta(days=1),
                today + timedelta(days=1),
            )

        self.assertEqual(client.get.await_count, 2)
        self.assertEqual(client.get.await_args_list[0].args[0], MODULE.ARCHIVE_URL)
        self.assertEqual(client.get.await_args_list[0].kwargs["params"]["end_date"], (today - timedelta(days=1)).isoformat())
        self.assertEqual(client.get.await_args_list[1].args[0], MODULE.FORECAST_URL)
        self.assertEqual(client.get.await_args_list[1].kwargs["params"]["start_date"], today.isoformat())


if __name__ == "__main__":
    unittest.main()