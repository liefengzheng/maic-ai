import sys
import unittest
import asyncio
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.main import app
from app.security import require_admin_user_id


class RegularUserDb:
    async def scalar(self, *_args, **_kwargs) -> str:
        return "user"


class AppSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_health(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})

    def test_conversations_require_authentication(self) -> None:
        response = self.client.get("/conversations")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"message": "未登录"})

    def test_agent_creation_requires_authentication(self) -> None:
        response = self.client.post("/agents", json={})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"message": "未登录"})

    def test_regular_user_cannot_manage_agents(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            asyncio.run(require_admin_user_id(uuid4(), RegularUserDb()))
        self.assertEqual(raised.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()