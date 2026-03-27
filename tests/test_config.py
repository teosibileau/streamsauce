"""Tests for configuration module."""

import dataclasses
import os

import pytest

from app.config import AMQPConfig, dbos_config


def test_amqp_config_url():
    config = AMQPConfig(
        host="myhost",
        port=5672,
        username="user",
        password="pass",
        exchange="amq.topic",
        queue_name="test.queue",
    )
    assert config.url == "amqp://user:pass@myhost:5672/"


def test_amqp_config_defaults():
    config = AMQPConfig(
        host="localhost",
        port=5672,
        username="guest",
        password="guest",
        exchange="amq.topic",
        queue_name="test",
    )
    assert config.routing_keys == []
    assert config.prefetch_count == 10


def test_amqp_config_frozen():
    config = AMQPConfig(
        host="localhost",
        port=5672,
        username="guest",
        password="guest",
        exchange="amq.topic",
        queue_name="test",
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        config.host = "other"


def test_amqp_config_from_env(monkeypatch):
    monkeypatch.setenv("AMQP_HOST", "custom-host")
    monkeypatch.setenv("AMQP_PORT", "5673")
    monkeypatch.setenv("AMQP_USERNAME", "admin")
    monkeypatch.setenv("AMQP_PASSWORD", "secret")
    monkeypatch.setenv("AMQP_EXCHANGE", "custom.exchange")
    monkeypatch.setenv("AMQP_QUEUE", "custom.queue")
    monkeypatch.setenv("AMQP_ROUTING_KEYS", "a.*.b,c.*.d")
    monkeypatch.setenv("AMQP_PREFETCH", "20")

    config = AMQPConfig(
        host=os.environ.get("AMQP_HOST", "broker"),
        port=int(os.environ.get("AMQP_PORT", "5672")),
        username=os.environ.get("AMQP_USERNAME", "guest"),
        password=os.environ.get("AMQP_PASSWORD", "guest"),
        exchange=os.environ.get("AMQP_EXCHANGE", "amq.topic"),
        queue_name=os.environ.get("AMQP_QUEUE", "streamsauce.cv"),
        routing_keys=os.environ.get("AMQP_ROUTING_KEYS", "").split(","),
        prefetch_count=int(os.environ.get("AMQP_PREFETCH", "10")),
    )

    assert config.host == "custom-host"
    assert config.port == 5673
    assert config.username == "admin"
    assert config.password == "secret"
    assert config.exchange == "custom.exchange"
    assert config.queue_name == "custom.queue"
    assert config.routing_keys == ["a.*.b", "c.*.d"]
    assert config.prefetch_count == 20


def test_amqp_config_routing_keys_split():
    keys = "streamchop.*.snapshot,streamchop.*.segment".split(",")
    config = AMQPConfig(
        host="localhost",
        port=5672,
        username="guest",
        password="guest",
        exchange="amq.topic",
        queue_name="test",
        routing_keys=keys,
    )
    assert config.routing_keys == ["streamchop.*.snapshot", "streamchop.*.segment"]


def test_dbos_config_defaults():
    assert dbos_config["name"] == "streamsauce"
    assert "database_url" in dbos_config
