import sys
import unittest
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import HTTPException

from app.agent_catalog import delete_skill


class ScalarResult:
    def __init__(self, value: object) -> None:
        self.value = value

    def scalar_one_or_none(self) -> object:
        return self.value


class SkillDeleteDb:
    def __init__(self, *, exists: bool = True, assigned: bool = False) -> None:
        self.exists = exists
        self.assigned = assigned
        self.deleted = False
        self.committed = False
        self.rolled_back = False

    async def execute(self, statement: object, *_args: object, **_kwargs: object) -> ScalarResult:
        sql = str(statement)
        if "FOR UPDATE" in sql:
            return ScalarResult(1 if self.exists else None)
        if "DELETE FROM skill_registry" in sql:
            self.deleted = True
        return ScalarResult(None)

    async def scalar(self, *_args: object, **_kwargs: object) -> bool:
        return self.assigned

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class SkillCatalogTests(unittest.IsolatedAsyncioTestCase):
    async def test_deletes_an_unassigned_skill(self) -> None:
        db = SkillDeleteDb()

        await delete_skill(1, uuid4(), db)  # type: ignore[arg-type]

        self.assertTrue(db.deleted)
        self.assertTrue(db.committed)

    async def test_rejects_deleting_an_assigned_skill(self) -> None:
        db = SkillDeleteDb(assigned=True)

        with self.assertRaises(HTTPException) as raised:
            await delete_skill(1, uuid4(), db)  # type: ignore[arg-type]

        self.assertEqual(raised.exception.status_code, 409)
        self.assertFalse(db.deleted)
        self.assertTrue(db.rolled_back)

    async def test_reports_a_missing_skill(self) -> None:
        db = SkillDeleteDb(exists=False)

        with self.assertRaises(HTTPException) as raised:
            await delete_skill(1, uuid4(), db)  # type: ignore[arg-type]

        self.assertEqual(raised.exception.status_code, 404)
        self.assertTrue(db.rolled_back)


if __name__ == "__main__":
    unittest.main()