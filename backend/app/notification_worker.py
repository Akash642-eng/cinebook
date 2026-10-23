import json
import logging
import os
import time

import pika
from pika.exceptions import AMQPConnectionError, AMQPChannelError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("cinebook.notifications")

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "cinebook")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD")
QUEUE_NAME = "cinebook.notifications"


def process_message(body: bytes) -> None:
    event = json.loads(body.decode("utf-8"))

    event_type = event.get("event_type")
    event_id = event.get("event_id")
    payload = event.get("payload")

    if not isinstance(event_type, str) or not event_type:
        raise ValueError("event_type is required")

    if not isinstance(event_id, str) or not event_id:
        raise ValueError("event_id is required")

    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")

    # Day 5 currently logs notifications. Email/SMS delivery is a later step.
    logger.info(
        "Notification processed: event_id=%s event_type=%s payload=%s",
        event_id,
        event_type,
        json.dumps(payload, separators=(",", ":"), sort_keys=True),
    )


def main() -> None:
    if not RABBITMQ_PASSWORD:
        raise RuntimeError("RABBITMQ_PASSWORD must be configured")

    credentials = pika.PlainCredentials(
        RABBITMQ_USER,
        RABBITMQ_PASSWORD,
    )

    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials,
        heartbeat=30,
        blocked_connection_timeout=30,
        connection_attempts=5,
        retry_delay=3,
    )

    while True:
        connection = None

        try:
            logger.info("Connecting to RabbitMQ at %s:%s", RABBITMQ_HOST, RABBITMQ_PORT)
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()

            channel.queue_declare(
                queue=QUEUE_NAME,
                durable=True,
            )

            channel.basic_qos(prefetch_count=1)

            def callback(ch, method, properties, body):
                try:
                    process_message(body)
                except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
                    logger.exception(
                        "Invalid notification message; rejecting without requeue"
                    )
                    ch.basic_nack(
                        delivery_tag=method.delivery_tag,
                        requeue=False,
                    )
                except Exception:
                    logger.exception(
                        "Notification processing failed; requeueing message"
                    )
                    ch.basic_nack(
                        delivery_tag=method.delivery_tag,
                        requeue=True,
                    )
                else:
                    ch.basic_ack(delivery_tag=method.delivery_tag)

            channel.basic_consume(
                queue=QUEUE_NAME,
                on_message_callback=callback,
                auto_ack=False,
            )

            logger.info("Listening on durable queue %s", QUEUE_NAME)
            channel.start_consuming()

        except (AMQPConnectionError, AMQPChannelError, OSError):
            logger.exception("RabbitMQ connection/channel error; retrying in 5 seconds")
            time.sleep(5)
        finally:
            if connection is not None and connection.is_open:
                connection.close()


if __name__ == "__main__":
    main()
