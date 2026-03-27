"""AMQP consumer for streamchop events."""

import json
import logging

import aio_pika
from aio_pika.abc import AbstractIncomingMessage
from dbos import DBOS, SetWorkflowID

from .config import AMQPConfig
from .schemas import SegmentEvent, SnapshotEvent, parse_routing_key
from .workflows import process_segment, process_snapshot

logger = logging.getLogger(__name__)


class AMQPConsumer:
    def __init__(self, config: AMQPConfig):
        self.config = config
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.Channel | None = None

    async def start(self) -> None:
        logger.info(
            "Connecting to AMQP at %s",
            self.config.url.replace(self.config.password, "***"),
        )
        self._connection = await aio_pika.connect_robust(self.config.url)
        logger.info("AMQP connected")
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=self.config.prefetch_count)

        exchange = await self._channel.get_exchange(self.config.exchange)
        logger.info("Using exchange: %s", self.config.exchange)

        queue = await self._channel.declare_queue(self.config.queue_name, durable=True)
        logger.info(
            "Declared queue: %s (messages: %d, consumers: %d)",
            queue.name,
            queue.declaration_result.message_count,
            queue.declaration_result.consumer_count,
        )

        for rk in self.config.routing_keys:
            await queue.bind(exchange, routing_key=rk)
            logger.info(
                "Bound queue %s to %s with key %s",
                self.config.queue_name,
                self.config.exchange,
                rk,
            )

        await queue.consume(self._on_message)
        logger.info("AMQP consumer started, waiting for messages...")

    async def _on_message(self, message: AbstractIncomingMessage) -> None:
        async with message.process(requeue=True):
            routing_key = message.routing_key or ""
            camera_id, event_type = parse_routing_key(routing_key)
            body = json.loads(message.body)

            if event_type == "snapshot":
                event = SnapshotEvent(**body)
                wf_id = event.idempotency_key
                with SetWorkflowID(wf_id):
                    DBOS.start_workflow(
                        process_snapshot,
                        event.camera_id,
                        event.snapshot_url,
                        event.snapshot_epoch,
                        event.segment_url,
                        event.segment_epoch,
                    )
            elif event_type == "segment":
                event = SegmentEvent(**body)
                wf_id = event.idempotency_key
                with SetWorkflowID(wf_id):
                    DBOS.start_workflow(
                        process_segment,
                        event.camera_id,
                        event.segment_url,
                        event.segment_epoch,
                        event.playlist,
                    )
            else:
                logger.warning("Unknown event type: %s", event_type)
                return

            logger.info(
                "Dispatched workflow %s for %s/%s", wf_id, camera_id, event_type
            )

    async def stop(self) -> None:
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
        logger.info("AMQP consumer stopped.")
