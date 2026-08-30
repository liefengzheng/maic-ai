from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .schemas import WorkshopBookingInput

router = APIRouter(tags=["workshops"])


@router.get("/workshop-slots")
async def list_slots(db: Annotated[AsyncSession, Depends(get_db)]) -> list[dict[str, Any]]:
    rows = (await db.execute(text(
        "SELECT id, starts_at, ends_at, capacity, remaining_seats, location "
        "FROM workshop_slots WHERE starts_at > now() AND remaining_seats > 0 ORDER BY starts_at"
    ))).mappings()
    return [dict(row) for row in rows]


@router.post("/workshop-bookings", status_code=status.HTTP_201_CREATED)
async def create_booking(
    data: WorkshopBookingInput,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    booking_id = (await db.execute(text("""
        INSERT INTO workshop_bookings
            (slot_id, name, organization, contact, attendee_count, topic, note)
        VALUES (:slot_id, :name, :organization, :contact, :attendee_count, :topic, :note)
        RETURNING id
    """), data.model_dump())).scalar_one()
    await db.commit()
    return {"id": booking_id}