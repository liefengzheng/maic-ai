import sys
import unittest
import asyncio
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.main import app
from app.conversations import _claim_conversation_run
from app.security import require_admin_user_id


class RegularUserDb:
    async def scalar(self, *_args, **_kwargs) -> str:
        return "user"


class RunClaimDb:
    def __init__(self, claimed_run_id: object) -> None:
        self.claimed_run_id = claimed_run_id

    async def scalar(self, *_args, **_kwargs) -> object:
        return self.claimed_run_id


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


class ConversationRunTests(unittest.IsolatedAsyncioTestCase):
    async def test_claims_an_idle_conversation(self) -> None:
        conversation_id = uuid4()
        run_id = uuid4()

        claimed = await _claim_conversation_run(
            RunClaimDb(run_id),  # type: ignore[arg-type]
            conversation_id,
            run_id,
        )

        self.assertTrue(claimed)

    async def test_rejects_a_concurrent_run(self) -> None:
        claimed = await _claim_conversation_run(
            RunClaimDb(None),  # type: ignore[arg-type]
            uuid4(),
            uuid4(),
        )

        self.assertFalse(claimed)


if __name__ == "__main__":
    unittest.main()