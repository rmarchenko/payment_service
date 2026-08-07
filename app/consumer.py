import asyncio
import random
import logging
import httpx
from datetime import datetime, UTC
import uuid
from faststream import FastStream
from sqlalchemy import update
from app.broker import broker, main_queue, main_exchange, dlq_exchange, dlq_queue
from app.database import AsyncSessionLocal
from app.models import Payment, PaymentStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastStream(broker)

async def send_webhook_with_retry(url: str, payload: dict, max_retries=3) -> bool:
    """Отправка вебхука с экспоненциальной задержкой"""
    async with httpx.AsyncClient() as client:
        for attempt in range(max_retries):
            try:
                response = await client.post(url, json=payload, timeout=5.0)
                if response.status_code in [200, 201, 202]:
                    logger.info(f"Webhook delivered successfully to {url}")
                    return True
            except httpx.RequestError as e:
                logger.warning(f"Attempt {attempt + 1} failed for webhook {url}: {e}")

            if attempt < max_retries - 1:
                sleep_time = 2 ** attempt
                await asyncio.sleep(sleep_time)
        return False

@broker.subscriber(main_queue, exchange=main_exchange)
async def process_payment_handler(data: dict):
    payment_id = data.get("payment_id")
    logger.info(f"Processing payment: {payment_id}")

    # 1. Эмуляция долгого процессинга шлюза (2-5 сек)
    await asyncio.sleep(random.uniform(2.0, 5.0))

    # 2. Определение исхода (90% Успех / 10% Ошибка)
    final_status = PaymentStatus.SUCCEEDED if random.random() < 0.9 else PaymentStatus.FAILED

    # 3. Обновление статуса в БД
    async with AsyncSessionLocal() as session:
        stmt = (
            update(Payment)
            .where(Payment.id == uuid.UUID(payment_id))
            .values(status=final_status, processed_at=datetime.now(UTC).replace(tzinfo=None))
            .returning(Payment.webhook_url, Payment.amount, Payment.currency)
        )
        res = await session.execute(stmt)
        row = res.fetchone()
        await session.commit()

    if not row:
        logger.error(f"Payment {payment_id} not found in database!")
        return

    webhook_url, amount, currency = row

    # 4. Отправка вебхука клиенту
    webhook_payload = {
        "payment_id": payment_id,
        "status": str(final_status),
        "amount": float(amount),
        "currency": currency,
        "timestamp": datetime.now(UTC).isoformat()
    }

    success = await send_webhook_with_retry(webhook_url, webhook_payload)
    if not success:
        raise RuntimeError(f"Webhook delivery failed for payment {payment_id}")

@broker.subscriber(dlq_queue, exchange=dlq_exchange)
async def dead_letter_handler(data: dict):
    logger.error(f"CRITICAL: Message moved to DLQ: {data}")