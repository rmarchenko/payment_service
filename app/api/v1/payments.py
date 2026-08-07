import uuid
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import Payment, OutboxEvent, PaymentStatus
from app.schemas import PaymentCreate, PaymentResponse, PaymentDetailResponse
from app.security import verify_api_key

router = APIRouter(prefix="/api/v1/payments", tags=["payments"], dependencies=[Depends(verify_api_key)])

@router.post("", response_model=PaymentResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_payment(
        payload: PaymentCreate,
        idempotency_key: str = Header(..., alias="Idempotency-Key"),
        db: AsyncSession = Depends(get_db)
):
    stmt = select(Payment).where(Payment.idempotency_key == idempotency_key)
    result = await db.execute(stmt)
    existing_payment = result.scalar_one_or_none()

    if existing_payment:
        return existing_payment

    payment_id = uuid.uuid4()
    new_payment = Payment(
        id=payment_id,
        amount=payload.amount,
        currency=payload.currency,
        description=payload.description,
        metadata_json=payload.metadata,
        idempotency_key=idempotency_key,
        webhook_url=str(payload.webhook_url),
        status=PaymentStatus.PENDING
    )

    outbox_event = OutboxEvent(
        event_type="payments.new",
        payload={"payment_id": str(payment_id)}
    )

    db.add(new_payment)
    db.add(outbox_event)

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Database error during billing transaction")

    await db.refresh(new_payment)
    return new_payment

@router.get("/{payment_id}", response_model=PaymentDetailResponse)
async def get_payment(payment_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(Payment).where(Payment.id == payment_id)
    result = await db.execute(stmt)
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    return payment
