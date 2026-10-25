import json
import logging
import os
from uuid import uuid4

import pika
from pika.exceptions import AMQPError

logger = logging.getLogger("cinebook.events")

EXCHANGE_NAME = "cinebook.events.v2"
QUEUE_NAME = "cinebook.notifications.v2"


def publish_event(event_type: str, payload: dict) -> bool:
    password = os.getenv("RABBITMQ_PASSWORD")

    if not password:
        logger.warning("RabbitMQ password missing; event was not published")
        return False

    event = {
        "event_id": str(uuid4()),
        "event_type": event_type,
        "payload": payload,
    }

    connection = None

    try:
        credentials = pika.PlainCredentials(
            os.getenv("RABBITMQ_USER", "cinebook"),
            password,
        )

        parameters = pika.ConnectionParameters(
            host=os.getenv("RABBITMQ_HOST", "rabbitmq"),
            port=int(os.getenv("RABBITMQ_PORT", "5672")),
            credentials=credentials,
            heartbeat=15,
            blocked_connection_timeout=5,
            socket_timeout=5,
            connection_attempts=1,
        )

        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        channel.exchange_declare(
            exchange=EXCHANGE_NAME,
            exchange_type="direct",
            durable=True,
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

        channel.confirm_delivery()

        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key="notification",
            body=json.dumps(event, separators=(",", ":")),
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,
                message_id=event["event_id"],
                type=event_type,
                headers={"x-retry-count": 0},
            ),
            mandatory=True,
        )

        logger.info(
            "Published event_id=%s event_type=%s",
            event["event_id"],
            event_type,
        )
        return True

    except (AMQPError, OSError, ValueError) as exc:
        logger.warning(
            "Could not publish event_type=%s error=%s",
            event_type,
            type(exc).__name__,
        )
        return False

    finally:
        if connection is not None and connection.is_open:
            try:
                connection.close()
            except AMQPError:
                logger.warning("Could not close RabbitMQ connection cleanly")
