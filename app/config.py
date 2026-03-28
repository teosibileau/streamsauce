import logging
import os
from dataclasses import dataclass, field

import colorlog
from dbos import DBOSConfig
from dotenv import load_dotenv

load_dotenv()

# DBOS Configuration
dbos_config: DBOSConfig = {
    "name": "streamsauce",
    "database_url": os.environ.get(
        "DBOS_DATABASE_URL", "postgresql://dbos:dbos@0.0.0.0:5432/dbos"
    ),
}


# AMQP Configuration
@dataclass(frozen=True)
class AMQPConfig:
    host: str
    port: int
    username: str
    password: str
    exchange: str
    queue_name: str
    routing_keys: list[str] = field(default_factory=list)
    prefetch_count: int = 10

    @property
    def url(self) -> str:
        return f"amqp://{self.username}:{self.password}@{self.host}:{self.port}/"  # noqa: E231


amqp_config = AMQPConfig(
    host=os.environ.get("AMQP_HOST", "broker"),
    port=int(os.environ.get("AMQP_PORT", "5672")),
    username=os.environ.get("AMQP_USERNAME", "guest"),
    password=os.environ.get("AMQP_PASSWORD", "guest"),
    exchange=os.environ.get("AMQP_EXCHANGE", "amq.topic"),
    queue_name=os.environ.get("AMQP_QUEUE", "streamsauce.cv"),
    routing_keys=os.environ.get(
        "AMQP_ROUTING_KEYS", "streamchop.*.snapshot,streamchop.*.segment"
    ).split(","),
    prefetch_count=int(os.environ.get("AMQP_PREFETCH", "10")),
)


# ONNX Configuration
@dataclass(frozen=True)
class OnnxConfig:
    model_path: str
    execution_provider: str
    confidence_threshold: float


onnx_config = OnnxConfig(
    model_path=os.environ.get("ONNX_MODEL_PATH", ".data/yolo11n.onnx"),
    execution_provider=os.environ.get(
        "ONNX_EXECUTION_PROVIDER", "CPUExecutionProvider"
    ),
    confidence_threshold=float(os.environ.get("ONNX_CONFIDENCE_THRESHOLD", "0.25")),
)


# Logging Setup
logger = logging.getLogger("app")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
handler.setLevel(logging.INFO)

formatter = colorlog.ColoredFormatter(
    "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    log_colors={
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "red,bg_white",
    },
)
handler.setFormatter(formatter)
logger.addHandler(handler)
