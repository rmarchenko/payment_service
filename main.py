import contextlib
import logging
from fastapi import FastAPI, Request
from app.api.v1 import payments
from app.broker import broker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webhook_sink")

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    await broker.connect()
    yield
    await broker.close()

app = FastAPI(title="Async Payment Service", lifespan=lifespan)
app.include_router(payments.router)
