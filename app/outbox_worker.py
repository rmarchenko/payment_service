import asyncio
import logging
from sqlalchemy import select, update
from app.database import AsyncSessionLocal
from app.models import OutboxEvent
from app.broker import broker, main_exchange

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def relay_outbox_events():
    await broker.connect()
    logger.info("Outbox worker started.")

    while True:
        async with AsyncSessionLocal() as session:
            stmt = select(OutboxEvent).where(OutboxEvent.processed == False).limit(10).with_for_update(skip_locked=True)
            result = await session.execute(stmt)
            events = result.scalars().all()

            if not events:
                await asyncio.sleep(1)
                continue

            for event in events:
                try:
                    await broker.publish(
                        message=event.payload,
                        queue="payments.new",
                        exchange=main_exchange,
                        routing_key="payment_new"
                    )
                    event.processed = True
                except Exception as e:
                    logger.error(f"Failed to publish event {event.id}: {e}")

            await session.commit()
        await asyncio.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(relay_outbox_events())
