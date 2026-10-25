import json
import logging
import os

import pika
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import SessionLocal
from app.event_models import ProcessedEvent


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("cinebook.worker")

EXCHANGE_NAME = "cinebook.events.v2"
QUEUE_NAME = "cinebook.notifications.v2"
RETRY_QUEUE = "cinebook.notifications.retry"
DLQ_QUEUE = "cinebook.notifications.dlq"
MAX_ATTEMPTS = 3
RETRY_DELAY_MS = 10000


def declare_topology(channel):
    channel.exchange_declare(
        exchange=EXCHANGE_NAME,
        exchange_type="direct",
        durable=True,
    )

    channel.queue_declare(
        queue=DLQ_QUEUE,
        durable=True,
    )
    channel.queue_bind(
        queue=DLQ_QUEUE,
        exchange=EXCHANGE_NAME,
        routing_key="dead",
    )

    channel.queue_declare(
        queue=RETRY_QUEUE,
        durable=True,
        arguments={
            "x-message-ttl": RETRY_DELAY_MS,
            "x-dead-letter-exchange": EXCHANGE_NAME,
            "x-dead-letter-routing-key": "notification",
        },
    )

    channel.queue_bind(
        queue=RETRY_QUEUE,
        exchange=EXCHANGE_NAME,
        routing_key="retry",
    )

    channel.queue_declare(
        queue=QUEUE_NAME,
        durable=True,
        arguments={
            "x-dead-letter-exchange": EXCHANGE_NAME,
            "x-dead-letter-routing-key": "dead",
        },
    )

    channel.queue_bind(
        queue=QUEUE_NAME,
        exchange=EXCHANGE_NAME,
        routing_key="notification",
    )


def persist_event_once(event_id: str, event_type: str, payload: dict) -> bool:
    payload_json = json.dumps(
        payload,
        separators=(",", ":"),
        sort_keys=True,
    )

    with SessionLocal() as session:
        statement = (
            pg_insert(ProcessedEvent)
            .values(
                event_id=event_id,
                event_type=event_type,
                status="processed",
                payload_json=payload_json,
            )
            .on_conflict_do_nothing(
                index_elements=[ProcessedEvent.event_id]
            )
            .returning(ProcessedEvent.event_id)
        )
        inserted_id = session.execute(statement).scalar_one_or_none()
        session.commit()
        return inserted_id is not None


def process_message(channel, method, properties, body):
    try:
        event = json.loads(body)
        if not isinstance(event, dict):
            raise ValueError("Event must be a JSON object")

        event_id = event.get("event_id")
        event_type = event.get("event_type")
        payload = event.get("payload")

        if (
            not isinstance(event_id, str)
            or not event_id
            or len(event_id) > 36
            or not isinstance(event_type, str)
            or not event_type
            or len(event_type) > 100
            or not isinstance(payload, dict)
        ):
            raise ValueError("Invalid event schema")

    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        logger.error("Rejecting invalid message: %s", exc)
        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key="dead",
            body=body,
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,
                headers={"x-dead-letter-reason": "invalid-message"},
            ),
            mandatory=True,
        )
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    try:
        inserted = persist_event_once(event_id, event_type, payload)

        if inserted:
            logger.info(
                "Notification processed: event_type=%s event_id=%s",
                event_type,
                event_id,
            )
        else:
            logger.info(
                "Duplicate event ignored: event_type=%s event_id=%s",
                event_type,
                event_id,
            )

        channel.basic_ack(delivery_tag=method.delivery_tag)

    except Exception:
        logger.exception("Event processing failed")

        headers = properties.headers or {}
        attempt = int(headers.get("x-retry-count", 0))

        if attempt + 1 >= MAX_ATTEMPTS:
            destination = "dead"
            logger.error(
                "Maximum attempts reached; sending event_id=%s to DLQ",
                event_id,
            )
        else:
            destination = "retry"
            logger.warning(
                "Scheduling retry %s/%s for event_id=%s",
                attempt + 1,
                MAX_ATTEMPTS - 1,
                event_id,
            )

        try:
            published = channel.basic_publish(
                exchange=EXCHANGE_NAME,
                routing_key=destination,
                body=body,
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=2,
                    message_id=event_id,
                    type=event_type,
                    headers={"x-retry-count": attempt + 1},
                ),
                mandatory=True,
            )
            if published is False:
                raise RuntimeError("RabbitMQ did not confirm republished message")

            channel.basic_ack(delivery_tag=method.delivery_tag)

        except Exception:
            logger.exception("Could not route failed event; requeueing original")
            if channel.is_open:
                channel.basic_nack(
                    delivery_tag=method.delivery_tag,
                    requeue=True,
                )


def main():
    host = os.getenv("RABBITMQ_HOST", "localhost")
    port = int(os.getenv("RABBITMQ_PORT", "5672"))
    username = os.getenv("RABBITMQ_USER", "cinebook")
    password = os.getenv("RABBITMQ_PASSWORD")

    if not password:
        raise RuntimeError("RABBITMQ_PASSWORD is not configured")

    credentials = pika.PlainCredentials(username, password)
    parameters = pika.ConnectionParameters(
        host=host,
        port=port,
        credentials=credentials,
        heartbeat=30,
        blocked_connection_timeout=30,
        connection_attempts=5,
        retry_delay=3,
    )

    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    declare_topology(channel)
    channel.confirm_delivery()
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(
        queue=QUEUE_NAME,
        on_message_callback=process_message,
        auto_ack=False,
    )

    logger.info("CineBook notification worker started")
    logger.info("Consuming from queue: %s", QUEUE_NAME)
    logger.info("Retry limit: %s attempts", MAX_ATTEMPTS)

    try:
        channel.start_consuming()
    finally:
        if connection.is_open:
            connection.close()


if __name__ == "__main__":
    main()
