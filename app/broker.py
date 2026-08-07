from faststream.rabbit import RabbitBroker, RabbitQueue, RabbitExchange, ExchangeType
from app.config import settings

broker = RabbitBroker(settings.RABBITMQ_URL)

dlq_exchange = RabbitExchange("payments.dlx", type=ExchangeType.DIRECT, auto_delete=False)
dlq_queue = RabbitQueue(
    name="payments.dlq",
    routing_key="dead_letter",
    auto_delete=False
)

main_exchange = RabbitExchange("payments.tx", type=ExchangeType.DIRECT, auto_delete=False)
main_queue = RabbitQueue(
    name="payments.new",
    routing_key="payment_new",
    auto_delete=False,
    arguments={
        "x-dead-letter-exchange": "payments.dlx",
        "x-dead-letter-routing-key": "dead_letter"
    }
)
